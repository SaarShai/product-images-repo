#!/usr/bin/env python3
"""Outer-v7: punch true enclosed paper; keep pale wash; hard edges; hi-res review.

User 2026-07-09 on v6c:
  - full preview too low-res to review
  - many background areas NOT deleted (enclosed paper kept wrongly)
  - cut00 / fringe_pink still FAIL (white rim + wrong silhouette)

Method:
  1. Seeds = chromatic / darker paint.
  2. Reconstruct into non-pure-paper (keeps pale wash attached to paint).
  3. Do NOT fill holes — instead punch enclosed PURE paper (true BG pockets).
  4. Transparent = outer border-connected pure paper + punched enclosed pure paper.
  5. Binary alpha. Hard edge: cut pure-white rim + inward RGB decontam / unmatte.
  6. Review: large full composites (≥2400px) + ROI boards.
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
    seed_chroma_min: float = 5.0
    seed_luma_max: float = 240.0
    pure_chroma_max: float = 2.5
    pure_luma_min: float = 251.0
    hole_min_area: int = 24
    white_rim_cut_px: int = 2
    defringe_width: int = 5
    luma_cap: float = 232.0
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


def reconstruct_from_seeds(seeds: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    labels, count = ndi.label(allowed)
    if count == 0:
        return np.zeros_like(allowed, dtype=bool)
    touch = np.unique(labels[seeds & allowed])
    touch = touch[touch != 0]
    if touch.size == 0:
        return seeds & allowed
    return np.isin(labels, touch)


def punch_enclosed_pure(fg: np.ndarray, pure: np.ndarray, min_area: int) -> tuple[np.ndarray, int, int]:
    """Punch pure-paper components that sit inside FG (enclosed BG pockets)."""
    cand = pure & fg
    labels, count = ndi.label(cand)
    if count == 0:
        return fg, 0, 0
    areas = np.bincount(labels.ravel())
    punch_ids = [i for i in range(1, count + 1) if areas[i] >= min_area]
    if not punch_ids:
        return fg, 0, 0
    punched = np.isin(labels, punch_ids)
    return fg & ~punched, len(punch_ids), int(punched.sum())


def decontam_rim(rgb: np.ndarray, fg: np.ndarray, width: int, luma_cap: float) -> np.ndarray:
    """Replace near-white FG rim with inward paint; then luma-cap remaining bright rim."""
    out = rgb.copy()
    if not fg.any():
        return out
    luma, chroma = luma_chroma(rgb)
    dist_in = ndi.distance_transform_edt(fg)
    fringe = fg & (dist_in <= width) & (luma >= 215) & (chroma <= 40)
    safe = fg & (dist_in >= width + 4) & ((chroma >= 8) | (luma <= 225))
    if not safe.any():
        safe = fg & (dist_in >= width + 4)
    if fringe.any() and safe.any():
        _, nearest = ndi.distance_transform_edt(~safe, return_indices=True)
        yy, xx = nearest
        out[fringe] = rgb[yy[fringe], xx[fringe]]

    luma2, _ = luma_chroma(out)
    bright = fg & (dist_in <= width) & (luma2 > luma_cap)
    if bright.any():
        scale = luma_cap / np.maximum(luma2[bright], 1.0)
        out[bright] = np.clip(out[bright].astype(np.float32) * scale[:, None], 0, 255).astype(
            np.uint8
        )
    return out


def run_pipeline(rgb: np.ndarray, p: Params) -> tuple[np.ndarray, dict[str, Any]]:
    mean = paper_model(rgb)
    luma, chroma = luma_chroma(rgb)

    pure = (luma >= p.pure_luma_min) & (chroma <= p.pure_chroma_max)
    allowed = ~pure

    seeds = ((chroma >= p.seed_chroma_min) | (luma <= p.seed_luma_max)) & allowed
    grown = reconstruct_from_seeds(seeds, allowed)

    # Start FG = grown paint+wash. Outer pure paper is already outside grown.
    # Also treat border-connected pure as BG explicitly.
    outer_bg = border_connected(pure)
    fg = grown & ~outer_bg

    # Punch enclosed pure paper still inside FG (true holes between branches)
    fg, n_holes, hole_px = punch_enclosed_pure(fg, pure, p.hole_min_area)

    # Cut pure-white rim still on FG (kills opaque white halo without soft alpha)
    if p.white_rim_cut_px > 0:
        bg = ~fg
        pure_rim = fg & (luma >= p.pure_luma_min) & (chroma <= p.pure_chroma_max)
        cut = pure_rim & ndi.binary_dilation(bg, iterations=p.white_rim_cut_px)
        # also near-white rim 1px
        near = fg & (luma >= 248) & (chroma <= 4)
        cut |= near & ndi.binary_dilation(bg, iterations=1)
        fg = fg & ~cut

    # Drop tiny FG islands
    labels, count = ndi.label(fg)
    if count:
        areas = np.bincount(labels.ravel())
        keep = areas >= p.small_noise_area
        keep[0] = False
        fg = keep[labels]

    rgb_out = decontam_rim(rgb, fg, p.defringe_width, p.luma_cap)

    rgba = np.empty((*rgb.shape[:2], 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb_out
    rgba[:, :, 3] = np.where(fg, 255, 0).astype(np.uint8)

    metrics = {
        "paper_mean_rgb": [float(x) for x in mean],
        "seed_px": int(seeds.sum()),
        "grown_px": int(grown.sum()),
        "outer_bg_px": int(outer_bg.sum()),
        "hole_components": n_holes,
        "hole_px": hole_px,
        "fg_px": int(fg.sum()),
        "opaque_pct": float(100.0 * fg.mean()),
        "transparent_pct": float(100.0 * (~fg).mean()),
        "semi_pct": 0.0,
        "params": asdict(p),
    }
    return rgba, metrics


def composite_preview(rgba: np.ndarray, bg: np.ndarray) -> np.ndarray:
    rgb = rgba[:, :, :3].astype(np.float32)
    a = rgba[:, :, 3].astype(np.float32) / 255.0
    return np.clip(rgb * a[:, :, None] + bg.astype(np.float32) * (1.0 - a[:, :, None]), 0, 255).astype(
        np.uint8
    )


def save_full(path: Path, rgba: np.ndarray, bg: np.ndarray, max_side: int) -> None:
    prev = Image.fromarray(composite_preview(rgba, bg), "RGB")
    w, h = prev.size
    scale = min(1.0, max_side / max(w, h))
    if scale < 1.0:
        prev = prev.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    prev.save(path, quality=92)


def make_review(path: Path, rgba: np.ndarray, x: int, y: int, w: int, h: int, scale: int = 3) -> None:
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
    im.save(path, quality=93)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hole-min", type=int, default=24)
    ap.add_argument("--rim-cut", type=int, default=2)
    ap.add_argument("--defringe", type=int, default=5)
    ap.add_argument("--full-max", type=int, default=2800, help="max side for full review jpg")
    args = ap.parse_args()
    p = Params(
        hole_min_area=args.hole_min,
        white_rim_cut_px=args.rim_cut,
        defringe_width=args.defringe,
    )

    rgb_path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    rgb = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.uint8)
    rgba, metrics = run_pipeline(rgb, p)

    out_dir = REPO / "Images/candidates/image14-research/fusion-outer-v7"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    out_png = out_dir / f"14-outer-v7-h{p.hole_min_area}-r{p.white_rim_cut_px}-x4.png"
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    (out_dir / f"{out_png.stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    save_full(review / "14-outer-v7-full-gray.jpg", rgba, gray, args.full_max)
    save_full(review / "14-outer-v7-full-magenta.jpg", rgba, mag, args.full_max)
    # Extra: upper coral region at higher effective res for "lots of BG left" check
    h, w = rgba.shape[:2]
    upper = rgba[: h // 2, :, :]
    save_full(review / "14-outer-v7-upper-gray.jpg", upper, gray[: h // 2], args.full_max)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgb.shape[1] / x8_w, rgb.shape[0] / x8_h

    def sx8(x: int, y: int, ww: int, hh: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(ww * sx)), max(1, int(hh * sy))

    for name, box in [
        ("cut00", sx8(3601, 6253, 320, 400)),
        ("enclosed_tri", sx8(6452 - 128, 5548 - 128, 256, 256)),
        ("fringe_pink", sx8(4355 - 128, 5013 - 128, 256, 256)),
        # larger cut00 context — the white blob on the right of cut00
        ("cut00_wide", sx8(3500, 6100, 520, 520)),
    ]:
        make_review(review / f"14-outer-v7-{name}.jpg", rgba, *box, scale=3)

    drive = PRODUCT / "Images/candidates/image14-research/fusion-outer-v7"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)

    print(json.dumps({"out_png": str(out_png), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
