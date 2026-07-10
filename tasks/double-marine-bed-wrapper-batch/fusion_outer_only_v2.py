#!/usr/bin/env python3
"""Outer-only soft bg removal for watercolor on white.

User feedback 2026-07-09:
  - Interior 'holes' from punching enclosed white are WRONG — keep them.
  - Soft-band color-to-alpha halo edges are WRONG.
  - Soft alpha is allowed; priority is no wrong-delete / no halo.

Method:
  1. PAPER = corner-calibrated near-white, low chroma.
  2. Only border-connected PAPER → transparent (outer background).
  3. Do NOT punch enclosed white (keeps white pockets / pale wash inside art).
  4. All non-outer-paper → fully opaque (alpha 255).
  5. Edge: tiny unknown band + GIMP unmatte ONLY there, with aggressive
     RGB unblend so partial-alpha pixels are paint-colored (no white rim).
     Optional 1px hard erode before soft band to eat white-mixed edge.
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
    paper_chroma_max: float = 6.0
    paper_luma_min: float = 247.0
    paper_dist_max: float = 10.0
    hard_erode_px: int = 1
    soft_band_px: int = 2
    small_fg_min_area: int = 16


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


def color_to_alpha(rgb: np.ndarray, paper: np.ndarray) -> np.ndarray:
    diff = np.abs(rgb.astype(np.float32) - paper.astype(np.float32)[None, None, :])
    return np.clip(diff.max(axis=2) / 255.0, 0.0, 1.0)


def unblend(rgb: np.ndarray, alpha: np.ndarray, paper: np.ndarray) -> np.ndarray:
    a = np.maximum(alpha, 1e-3)[:, :, None]
    out = (rgb.astype(np.float32) - (1.0 - a) * paper.astype(np.float32)[None, None, :]) / a
    return np.clip(out, 0, 255).astype(np.uint8)


def run_pipeline(rgb: np.ndarray, p: Params) -> tuple[np.ndarray, dict[str, Any]]:
    mean, std = paper_model(rgb)
    luma, chroma = luma_chroma(rgb)
    dist = bg_distance(rgb, mean, std)

    paper = (luma >= p.paper_luma_min) & (chroma <= p.paper_chroma_max) & (dist <= p.paper_dist_max)
    flood_bg = border_connected(paper)

    # Outer-only: FG is everything not outer paper. Keep enclosed white.
    fg = ~flood_bg
    if p.hard_erode_px > 0:
        fg = ndi.binary_erosion(fg, iterations=p.hard_erode_px)

    # Drop tiny FG islands (noise)
    labels, count = ndi.label(fg)
    if count:
        areas = np.bincount(labels.ravel())
        keep = areas >= p.small_fg_min_area
        keep[0] = False
        fg = keep[labels]

    alpha = np.zeros(fg.shape, dtype=np.float32)
    alpha[fg] = 1.0

    # Soft band only at outer boundary (between FG and flood_bg)
    if p.soft_band_px > 0:
        # Pixels in FG within soft_band_px of background
        dist_in = ndi.distance_transform_edt(fg)
        band = fg & (dist_in <= p.soft_band_px)
        c2a = color_to_alpha(rgb, mean)
        # In band: use max(c2a, something) carefully — prefer paint retention:
        # alpha = c2a only where c2a is meaningful; raise floor so pale paint stays
        # Actually user hates halo: use c2a but then FULLY unblend RGB.
        alpha[band] = c2a[band]
        # Ensure deep interior stays 1
        alpha[fg & (dist_in > p.soft_band_px)] = 1.0

    rgb_out = rgb.copy()
    partial = (alpha > 0.0) & (alpha < 0.999)
    if partial.any():
        rgb_out[partial] = unblend(rgb, alpha, mean)[partial]
        # Extra: if unblended pixel still near paper, pull from deeper interior
        dist_in = ndi.distance_transform_edt(alpha > 0.5)
        safe = (alpha > 0.5) & (dist_in >= p.soft_band_px + 2)
        if safe.any():
            _, nearest = ndi.distance_transform_edt(~safe, return_indices=True)
            yy, xx = nearest
            still_bright = partial & (luma_chroma(rgb_out)[0] > 240)
            rgb_out[still_bright] = rgb[yy[still_bright], xx[still_bright]]

    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb_out
    rgba[:, :, 3] = np.clip(np.round(alpha * 255.0), 0, 255).astype(np.uint8)

    metrics = {
        "paper_mean_rgb": [float(x) for x in mean],
        "flood_bg_px": int(flood_bg.sum()),
        "fg_px": int(fg.sum()),
        "opaque_pct": float(100.0 * (rgba[:, :, 3] == 255).mean()),
        "transparent_pct": float(100.0 * (rgba[:, :, 3] == 0).mean()),
        "semi_pct": float(100.0 * ((rgba[:, :, 3] > 0) & (rgba[:, :, 3] < 255)).mean()),
        "enclosed_holes_punched": 0,
        "params": asdict(p),
    }
    return rgba, metrics


def composite_preview(rgba: np.ndarray, bg: np.ndarray) -> np.ndarray:
    rgb = rgba[:, :, :3].astype(np.float32)
    a = rgba[:, :, 3].astype(np.float32) / 255.0
    return np.clip(rgb * a[:, :, None] + bg.astype(np.float32) * (1.0 - a[:, :, None]), 0, 255).astype(
        np.uint8
    )


def make_review(path: Path, rgba: np.ndarray, x: int, y: int, w: int, h: int, scale: int = 2) -> None:
    patch = rgba[y : y + h, x : x + w]
    gray = np.full(patch.shape[:2] + (3,), 140, dtype=np.uint8)
    black = np.zeros_like(gray)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    src = patch[:, :, :3]
    board = np.concatenate(
        [src, composite_preview(patch, gray), composite_preview(patch, black), composite_preview(patch, mag)],
        axis=1,
    )
    im = Image.fromarray(board, "RGB")
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=92)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--erode", type=int, default=1)
    ap.add_argument("--soft-band", type=int, default=2)
    ap.add_argument("--hard-only", action="store_true", help="No soft band; binary outer cut + RGB decontam")
    args = ap.parse_args()
    p = Params(hard_erode_px=args.erode, soft_band_px=0 if args.hard_only else args.soft_band)

    rgb_path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    rgb = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.uint8)
    rgba, metrics = run_pipeline(rgb, p)

    tag = "hard" if args.hard_only else "soft"
    out_dir = REPO / "Images/candidates/image14-research/fusion-outer-v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    out_png = out_dir / f"14-outer-only-{tag}-e{p.hard_erode_px}-b{p.soft_band_px}-x4.png"
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    (out_dir / f"{out_png.stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    for name, bg in [("gray", gray), ("magenta", mag)]:
        prev = Image.fromarray(composite_preview(rgba, bg), "RGB")
        prev.thumbnail((1200, 2000), Image.Resampling.LANCZOS)
        prev.save(review / f"07-outer-{tag}-full-{name}.jpg", quality=90)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgb.shape[1] / x8_w, rgb.shape[0] / x8_h

    def sx8(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(w * sx)), max(1, int(h * sy))

    for name, box in [
        ("cut00", sx8(3601, 6253, 320, 400)),
        ("enclosed_tri", sx8(6452 - 128, 5548 - 128, 256, 256)),
        ("fringe_pink", sx8(4355 - 128, 5013 - 128, 256, 256)),
    ]:
        make_review(review / f"07-outer-{tag}-{name}.jpg", rgba, *box, scale=2)

    drive = PRODUCT / "Images/candidates/image14-research/fusion-outer-v2"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)

    print(json.dumps({"out_png": str(out_png), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
