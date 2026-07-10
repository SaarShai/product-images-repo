#!/usr/bin/env python3
"""Outer-v5: open paper bridges → flood can't leak; no soft halo.

User rejects: interior holes, soft/halo edges.

Root cause of silhouette bites:
  thin near-white wash bridges connect exterior paper into the art;
  flood walks those bridges and deletes pale paint.

Fix:
  1. Strict PAPER mask.
  2. binary_OPENING on paper → removes thin corridors (keeps thick exterior).
  3. Border-connected opened-paper → transparent only.
  4. Enclosed paper stays opaque (never punched).
  5. Binary alpha. Rim near-paper RGB → inward paint sample (no soft band).
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
    paper_dist_max: float = 10.0
    open_px: int = 4  # break corridors thinner than ~8px at x4
    white_rim_cut_px: int = 1  # drop pure-white FG rim into BG
    fringe_ring_px: int = 4
    fringe_luma_min: float = 225.0
    fringe_chroma_max: float = 28.0
    small_noise_area: int = 32


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


def run_pipeline(rgb: np.ndarray, p: Params) -> tuple[np.ndarray, dict[str, Any]]:
    mean, std = paper_model(rgb)
    luma, chroma = luma_chroma(rgb)
    dist = bg_distance(rgb, mean, std)

    paper = (luma >= p.paper_luma_min) & (chroma <= p.paper_chroma_max) & (dist <= p.paper_dist_max)

    # Break thin paper corridors so flood cannot enter the illustration
    if p.open_px > 0:
        struct = ndi.generate_binary_structure(2, 1)
        paper_open = ndi.binary_opening(paper, structure=struct, iterations=p.open_px)
    else:
        paper_open = paper

    true_bg = border_connected(paper_open)
    fg = ~true_bg

    # Optional: cut pure-white rim still sitting on FG (kills opaque white halo)
    if p.white_rim_cut_px > 0:
        pure = fg & (luma >= 253) & (chroma <= 2)
        if pure.any():
            touch = pure & ndi.binary_dilation(true_bg, iterations=p.white_rim_cut_px)
            fg = fg & ~touch
            true_bg = ~fg

    # Drop tiny FG speckles in the exterior
    labels, count = ndi.label(fg)
    if count:
        areas = np.bincount(labels.ravel())
        keep = areas >= p.small_noise_area
        keep[0] = False
        fg = keep[labels]
        true_bg = ~fg

    alpha = fg.astype(np.float32)
    rgb_out = rgb.copy()

    # Inward RGB sample on near-paper FG rim (binary alpha — no soft halo)
    if p.fringe_ring_px > 0 and fg.any():
        dist_in = ndi.distance_transform_edt(fg)
        fringe = (
            fg
            & (dist_in <= p.fringe_ring_px)
            & (luma >= p.fringe_luma_min)
            & (chroma <= p.fringe_chroma_max)
        )
        if fringe.any():
            safe = fg & (dist_in >= p.fringe_ring_px + 4) & (
                (chroma > 12) | (luma < 220)
            )
            if not safe.any():
                safe = fg & (dist_in >= p.fringe_ring_px + 4)
            if safe.any():
                _, nearest = ndi.distance_transform_edt(~safe, return_indices=True)
                yy, xx = nearest
                rgb_out[fringe] = rgb[yy[fringe], xx[fringe]]

    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb_out
    rgba[:, :, 3] = (alpha * 255.0).astype(np.uint8)

    metrics = {
        "paper_mean_rgb": [float(x) for x in mean],
        "paper_px": int(paper.sum()),
        "paper_open_px": int(paper_open.sum()),
        "true_bg_px": int(true_bg.sum()),
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
    board = np.concatenate(
        [
            patch[:, :, :3],
            composite_preview(patch, gray),
            composite_preview(patch, black),
            composite_preview(patch, mag),
        ],
        axis=1,
    )
    im = Image.fromarray(board, "RGB")
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, quality=92)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--open", type=int, default=4)
    ap.add_argument("--fringe", type=int, default=4)
    ap.add_argument("--white-rim", type=int, default=1)
    args = ap.parse_args()
    p = Params(open_px=args.open, fringe_ring_px=args.fringe, white_rim_cut_px=args.white_rim)

    rgb_path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    rgb = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.uint8)
    rgba, metrics = run_pipeline(rgb, p)

    out_dir = REPO / "Images/candidates/image14-research/fusion-outer-v5"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    out_png = out_dir / f"14-outer-v5-o{p.open_px}-f{p.fringe_ring_px}-x4.png"
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    (out_dir / f"{out_png.stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    for name, bg in [("gray", gray), ("magenta", mag)]:
        prev = Image.fromarray(composite_preview(rgba, bg), "RGB")
        prev.thumbnail((1200, 2000), Image.Resampling.LANCZOS)
        prev.save(review / f"10-outer-v5-full-{name}.jpg", quality=90)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgb.shape[1] / x8_w, rgb.shape[0] / x8_h

    def sx8(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(w * sx)), max(1, int(h * sy))

    for name, box in [
        ("cut00", sx8(3601, 6253, 320, 400)),
        ("enclosed_tri", sx8(6452 - 128, 5548 - 128, 256, 256)),
        ("fringe_pink", sx8(4355 - 128, 5013 - 128, 256, 256)),
    ]:
        make_review(review / f"10-outer-v5-{name}.jpg", rgba, *box, scale=2)

    drive = PRODUCT / "Images/candidates/image14-research/fusion-outer-v5"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)

    print(json.dumps({"out_png": str(out_png), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
