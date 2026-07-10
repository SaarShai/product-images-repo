#!/usr/bin/env python3
"""Outer-v6: grow FG from chromatic seeds into pale wash; stop at pure paper.

User rejects: wrong holes (pale paint deleted), soft/halo edges.

Idea:
  Pale wash is not paper — it is paint connected to chromatic coral.
  Pure paper (near 255, chroma≈0) is the only walkable BG.

  1. Seeds = chroma ≥ seed_chroma OR luma ≤ seed_luma_max (real paint).
  2. Reconstruct: keep non-paper components that touch seeds.
  3. Fill holes → enclosed white stays opaque.
  4. Transparent = border-connected exterior only.
  5. Binary alpha. Near-paper FG rim RGB ← inward chromatic sample.
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
    seed_chroma_min: float = 6.0
    seed_luma_max: float = 235.0
    pure_chroma_max: float = 2.0
    pure_luma_min: float = 252.0
    fringe_ring_px: int = 4
    fringe_luma_min: float = 220.0
    fringe_chroma_max: float = 30.0
    small_noise_area: int = 48


def luma_chroma(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb16 = rgb.astype(np.uint16)
    luma = ((77 * rgb16[:, :, 0] + 150 * rgb16[:, :, 1] + 29 * rgb16[:, :, 2]) >> 8).astype(
        np.float32
    )
    chroma = (rgb.max(2) - rgb.min(2)).astype(np.float32)
    return luma, chroma


def paper_model(rgb: np.ndarray) -> np.ndarray:
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
    return samples.mean(0)


def border_connected(mask: np.ndarray) -> np.ndarray:
    labels, count = ndi.label(mask)
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    ids = set(labels[0].tolist()) | set(labels[-1].tolist())
    ids |= set(labels[:, 0].tolist()) | set(labels[:, -1].tolist())
    ids.discard(0)
    return np.isin(labels, list(ids)) if ids else np.zeros_like(mask, dtype=bool)


def fill_holes(mask: np.ndarray) -> np.ndarray:
    inv = ~mask
    exterior = border_connected(inv)
    return mask | (inv & ~exterior)


def reconstruct_from_seeds(seeds: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """Keep allowed components that touch any seed (geodesic reconstruction)."""
    labels, count = ndi.label(allowed)
    if count == 0:
        return np.zeros_like(allowed, dtype=bool)
    touch = np.unique(labels[seeds & allowed])
    touch = touch[touch != 0]
    if touch.size == 0:
        return seeds & allowed
    return np.isin(labels, touch)


def run_pipeline(rgb: np.ndarray, p: Params) -> tuple[np.ndarray, dict[str, Any]]:
    mean = paper_model(rgb)
    luma, chroma = luma_chroma(rgb)

    pure_paper = (luma >= p.pure_luma_min) & (chroma <= p.pure_chroma_max)
    allowed = ~pure_paper

    seeds = (chroma >= p.seed_chroma_min) | (luma <= p.seed_luma_max)
    seeds &= allowed

    grown = reconstruct_from_seeds(seeds, allowed)
    fg = fill_holes(grown)

    labels, count = ndi.label(fg)
    if count:
        areas = np.bincount(labels.ravel())
        keep = areas >= p.small_noise_area
        keep[0] = False
        fg = keep[labels]

    true_bg = border_connected(~fg)
    fg = ~true_bg

    alpha = fg.astype(np.float32)
    rgb_out = rgb.copy()

    if p.fringe_ring_px > 0 and fg.any():
        dist_in = ndi.distance_transform_edt(fg)
        fringe = (
            fg
            & (dist_in <= p.fringe_ring_px)
            & (luma >= p.fringe_luma_min)
            & (chroma <= p.fringe_chroma_max)
        )
        if fringe.any():
            safe = fg & (dist_in >= p.fringe_ring_px + 5) & (
                (chroma >= p.seed_chroma_min) | (luma <= p.seed_luma_max)
            )
            if not safe.any():
                safe = fg & (dist_in >= p.fringe_ring_px + 5)
            if safe.any():
                _, nearest = ndi.distance_transform_edt(~safe, return_indices=True)
                yy, xx = nearest
                rgb_out[fringe] = rgb[yy[fringe], xx[fringe]]

    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb_out
    rgba[:, :, 3] = (alpha * 255.0).astype(np.uint8)

    metrics = {
        "paper_mean_rgb": [float(x) for x in mean],
        "seed_px": int(seeds.sum()),
        "grown_px": int(grown.sum()),
        "fg_px": int(fg.sum()),
        "true_bg_px": int(true_bg.sum()),
        "pure_paper_px": int(pure_paper.sum()),
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
    white = np.full(patch.shape[:2] + (3,), 255, dtype=np.uint8)
    gray = np.full(patch.shape[:2] + (3,), 140, dtype=np.uint8)
    black = np.zeros_like(gray)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    board = np.concatenate(
        [
            composite_preview(patch, white),
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
    ap.add_argument("--seed-chroma", type=float, default=6.0)
    ap.add_argument("--seed-luma", type=float, default=235.0)
    ap.add_argument("--pure-chroma", type=float, default=2.0)
    ap.add_argument("--pure-luma", type=float, default=252.0)
    ap.add_argument("--fringe", type=int, default=4)
    args = ap.parse_args()
    p = Params(
        seed_chroma_min=args.seed_chroma,
        seed_luma_max=args.seed_luma,
        pure_chroma_max=args.pure_chroma,
        pure_luma_min=args.pure_luma,
        fringe_ring_px=args.fringe,
    )

    rgb_path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    rgb = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.uint8)
    rgba, metrics = run_pipeline(rgb, p)

    out_dir = REPO / "Images/candidates/image14-research/fusion-outer-v6"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    out_png = out_dir / (
        f"14-outer-v6-sc{int(p.seed_chroma_min)}-pl{int(p.pure_luma_min)}-x4.png"
    )
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    (out_dir / f"{out_png.stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    for name, bg in [("gray", gray), ("magenta", mag)]:
        prev = Image.fromarray(composite_preview(rgba, bg), "RGB")
        prev.thumbnail((1200, 2000), Image.Resampling.LANCZOS)
        prev.save(review / f"11-outer-v6-full-{name}.jpg", quality=90)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgb.shape[1] / x8_w, rgb.shape[0] / x8_h

    def sx8(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(w * sx)), max(1, int(h * sy))

    for name, box in [
        ("cut00", sx8(3601, 6253, 320, 400)),
        ("enclosed_tri", sx8(6452 - 128, 5548 - 128, 256, 256)),
        ("fringe_pink", sx8(4355 - 128, 5013 - 128, 256, 256)),
    ]:
        make_review(review / f"11-outer-v6-{name}.jpg", rgba, *box, scale=2)

    drive = PRODUCT / "Images/candidates/image14-research/fusion-outer-v6"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)

    print(json.dumps({"out_png": str(out_png), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
