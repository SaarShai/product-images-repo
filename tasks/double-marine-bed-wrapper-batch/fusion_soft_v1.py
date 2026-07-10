#!/usr/bin/env python3
"""Soft-alpha watercolor bg removal: flood paper + edge unmatte, keep pale paint opaque.

Priority (user 2026-07-09): fix wrong-delete / enclosed holes / fringe.
Soft/semi-transparent edges ARE allowed. Binary alpha is NOT required.

Method:
  1. Corner-calibrated PAPER (near-white, low chroma).
  2. flood_bg = border-connected PAPER → alpha 0.
  3. enclosed PAPER → alpha 0 (true holes).
  4. Interior non-paper → alpha 255 (keeps pale coral / sand / wash).
  5. Soft color-to-alpha ONLY in a boundary band around flood_bg
     (removes white fringe without punching holes in pale paint).
  6. Un-blend RGB from paper in the soft band.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None

REPO = Path(__file__).resolve().parents[2]
PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)


@dataclass
class Params:
    paper_chroma_max: float = 5.0
    paper_luma_min: float = 248.0
    paper_dist_max: float = 8.0
    hole_chroma_max: float = 10.0
    hole_luma_min: float = 246.0
    hole_min_area: int = 8
    soft_band_px: int = 6
    soft_alpha_gamma: float = 1.0  # >1 keeps more paint in band
    small_fg_min_area: int = 8


def luma_chroma(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb16 = rgb.astype(np.uint16)
    luma = ((77 * rgb16[:, :, 0] + 150 * rgb16[:, :, 1] + 29 * rgb16[:, :, 2]) >> 8).astype(
        np.float32
    )
    chroma = (rgb.max(2) - rgb.min(2)).astype(np.float32)
    return luma, chroma


def paper_model(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = rgb.shape[:2]
    py, px = max(12, h // 50), max(12, w // 50)
    samples = np.concatenate(
        [
            rgb[:py, :px].reshape(-1, 3),
            rgb[:py, -px:].reshape(-1, 3),
            rgb[-py:, :px].reshape(-1, 3),
            rgb[-py:, -px:].reshape(-1, 3),
        ],
        axis=0,
    ).astype(np.float32)
    return samples.mean(0), np.maximum(samples.std(0), 1.0)


def bg_distance(rgb: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    z = (rgb.astype(np.float32) - mean[None, None, :]) / std[None, None, :]
    return np.sqrt((z * z).sum(2))


def border_connected(mask: np.ndarray) -> np.ndarray:
    labels, count = ndi.label(mask)
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    ids = set(labels[0].tolist()) | set(labels[-1].tolist())
    ids |= set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
    ids.discard(0)
    return np.isin(labels, list(ids)) if ids else np.zeros_like(mask, dtype=bool)


def punch_components(mask_to_clear: np.ndarray, min_area: int) -> np.ndarray:
    """Return True where components of mask_to_clear with area>=min_area should be cleared."""
    labels, count = ndi.label(mask_to_clear)
    if count == 0:
        return np.zeros_like(mask_to_clear, dtype=bool)
    areas = np.bincount(labels.ravel())
    keep = areas >= min_area
    keep[0] = False
    return keep[labels]


def color_to_alpha_channel(rgb: np.ndarray, paper: np.ndarray) -> np.ndarray:
    """GIMP-style: alpha = max_channel |C - paper| / 255, then unblend."""
    diff = np.abs(rgb.astype(np.float32) - paper.astype(np.float32)[None, None, :])
    alpha = diff.max(axis=2) / 255.0
    return np.clip(alpha, 0.0, 1.0)


def unblend_from_paper(rgb: np.ndarray, alpha: np.ndarray, paper: np.ndarray) -> np.ndarray:
    a = np.clip(alpha, 1e-3, 1.0)[:, :, None]
    out = (rgb.astype(np.float32) - (1.0 - a) * paper.astype(np.float32)[None, None, :]) / a
    return np.clip(out, 0, 255).astype(np.uint8)


def run_pipeline(rgb: np.ndarray, p: Params) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Return (rgba_uint8 HxWx4, metrics)."""
    mean, std = paper_model(rgb)
    luma, chroma = luma_chroma(rgb)
    dist = bg_distance(rgb, mean, std)

    paper_tight = (luma >= p.paper_luma_min) & (chroma <= p.paper_chroma_max) & (
        dist <= p.paper_dist_max
    )
    flood_bg = border_connected(paper_tight)

    paper_loose = (luma >= p.hole_luma_min) & (chroma <= p.hole_chroma_max) & (
        dist <= p.paper_dist_max + 2
    )
    enclosed = paper_loose & ~border_connected(paper_loose)
    hole_clear = punch_components(enclosed, p.hole_min_area)

    # Hard transparent: outer flood + enclosed holes
    hard_bg = flood_bg | hole_clear

    # Soft band: FG pixels near hard_bg (edge fringe zone only)
    dil = ndi.binary_dilation(hard_bg, iterations=p.soft_band_px)
    soft_band = dil & ~hard_bg

    # Base alpha: opaque everywhere except hard_bg
    alpha = np.ones(rgb.shape[:2], dtype=np.float32)
    alpha[hard_bg] = 0.0

    # Soft color-to-alpha only in band
    c2a = color_to_alpha_channel(rgb, mean)
    if p.soft_alpha_gamma != 1.0:
        c2a = np.power(c2a, p.soft_alpha_gamma)
    alpha[soft_band] = c2a[soft_band]

    # Drop tiny FG islands
    fg_hard = alpha > 0.02
    labels, count = ndi.label(fg_hard)
    if count:
        areas = np.bincount(labels.ravel())
        keep = areas >= p.small_fg_min_area
        keep[0] = False
        drop = ~keep[labels]
        alpha[drop] = 0.0

    rgb_out = rgb.copy()
    soft_or_partial = (alpha > 0.0) & (alpha < 0.999)
    if soft_or_partial.any():
        rgb_out[soft_or_partial] = unblend_from_paper(rgb, alpha, mean)[soft_or_partial]

    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb_out
    rgba[:, :, 3] = np.clip(np.round(alpha * 255.0), 0, 255).astype(np.uint8)

    metrics = {
        "paper_mean_rgb": [float(x) for x in mean],
        "flood_bg_px": int(flood_bg.sum()),
        "hole_px": int(hole_clear.sum()),
        "soft_band_px": int(soft_band.sum()),
        "opaque_pct": float(100.0 * (rgba[:, :, 3] == 255).mean()),
        "transparent_pct": float(100.0 * (rgba[:, :, 3] == 0).mean()),
        "semi_pct": float(100.0 * ((rgba[:, :, 3] > 0) & (rgba[:, :, 3] < 255)).mean()),
        "params": asdict(p),
    }
    return rgba, metrics


def make_review(
    out_path: Path, rgba: np.ndarray, x: int, y: int, w: int, h: int, scale: int = 2
) -> None:
    patch = rgba[y : y + h, x : x + w]
    rgb = patch[:, :, :3].astype(np.float32)
    a = patch[:, :, 3].astype(np.float32) / 255.0
    a3 = a[:, :, None]

    def comp(bg: np.ndarray) -> np.ndarray:
        return np.clip(rgb * a3 + bg.astype(np.float32) * (1.0 - a3), 0, 255).astype(np.uint8)

    gray = np.full_like(rgb, 140, dtype=np.uint8)
    black = np.zeros_like(rgb, dtype=np.uint8)
    mag = np.zeros_like(rgb, dtype=np.uint8)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    src = rgb.astype(np.uint8)
    board = np.concatenate([src, comp(gray), comp(black), comp(mag)], axis=1)
    im = Image.fromarray(board, "RGB")
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, quality=92)


def load_image14_x4() -> np.ndarray:
    path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--soft-band", type=int, default=6)
    ap.add_argument("--gamma", type=float, default=1.0)
    args = ap.parse_args()
    p = Params(soft_band_px=args.soft_band, soft_alpha_gamma=args.gamma)

    rgb = load_image14_x4()
    rgba, metrics = run_pipeline(rgb, p)

    out_dir = REPO / "Images/candidates/image14-research/fusion-soft-v1"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    out_png = out_dir / "14-soft-flood-edge-unmatte-x4.png"
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    (out_dir / "14-soft-flood-edge-unmatte-x4-metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    # Full gray preview
    a = rgba[:, :, 3].astype(np.float32) / 255.0
    gray = np.full_like(rgba[:, :, :3], 140, dtype=np.float32)
    comp = rgba[:, :, :3].astype(np.float32) * a[:, :, None] + gray * (1.0 - a[:, :, None])
    prev = Image.fromarray(np.clip(comp, 0, 255).astype(np.uint8), "RGB")
    prev.thumbnail((1200, 2000), Image.Resampling.LANCZOS)
    prev.save(review / "05-soft-v1-full-gray.jpg", quality=90)

    # Magenta full preview (fringe / over-delete visible)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    comp_m = rgba[:, :, :3].astype(np.float32) * a[:, :, None] + mag * (1.0 - a[:, :, None])
    prev_m = Image.fromarray(np.clip(comp_m, 0, 255).astype(np.uint8), "RGB")
    prev_m.thumbnail((1200, 2000), Image.Resampling.LANCZOS)
    prev_m.save(review / "05-soft-v1-full-magenta.jpg", quality=90)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgb.shape[1] / x8_w, rgb.shape[0] / x8_h

    def sx8(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(w * sx)), max(1, int(h * sy))

    rois = [
        ("cut00", *sx8(3601, 6253, 320, 400)),
        ("enclosed_tri", *sx8(6452 - 128, 5548 - 128, 256, 256)),
        ("fringe_pink", *sx8(4355 - 128, 5013 - 128, 256, 256)),
        ("sand_base", *sx8(2000, 12000, 800, 600)),
    ]
    for name, x, y, w, h in rois:
        make_review(review / f"05-soft-v1-{name}.jpg", rgba, x, y, w, h, scale=2)

    # Drive mirror
    drive = PRODUCT / "Images/candidates/image14-research/fusion-soft-v1"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)

    print(json.dumps({"out_png": str(out_png), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
