#!/usr/bin/env python3
"""Outer-v8: punch near-white enclosed BG; restore pale paint; hard rim cut.

User on v6c/v7:
  - full too low-res (use ≥3200 + upper crop + PNG path)
  - many BG areas not deleted (near-white pockets kept as 'wash')
  - cut00 / fringe_pink FAIL (white rim / concave white left)

Method:
  1. LOOSE paper (near-white) → outer flood transparent.
  2. Punch enclosed LOOSE paper (true BG between branches).
  3. Restore paint-like components wrongly punched (chroma/luma/dist).
  4. Hard rim: FG pixels near BG that are still near-white → transparent.
  5. Remaining rim RGB: inward sample + luma cap (binary alpha, no soft halo).
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
    paper_luma_min: float = 246.0
    paper_dist_max: float = 12.0
    hole_min_area: int = 20
    restore_min_chroma: float = 3.5
    restore_max_luma: float = 247.0
    restore_min_dist: float = 3.0
    restore_min_area: int = 12
    restore_max_area: int = 80_000
    rim_cut_px: int = 3
    rim_cut_luma: float = 238.0
    rim_cut_chroma: float = 18.0
    defringe_width: int = 6
    luma_cap: float = 220.0
    small_noise_area: int = 40


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


def punch_components(mask: np.ndarray, min_area: int) -> np.ndarray:
    labels, count = ndi.label(mask)
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    areas = np.bincount(labels.ravel())
    keep = [i for i in range(1, count + 1) if areas[i] >= min_area]
    return np.isin(labels, keep) if keep else np.zeros_like(mask, dtype=bool)


def restore_paint(
    fg: np.ndarray,
    punched: np.ndarray,
    luma: np.ndarray,
    chroma: np.ndarray,
    dist: np.ndarray,
    p: Params,
) -> tuple[np.ndarray, int, int]:
    labels, count = ndi.label(punched)
    if count == 0:
        return fg, 0, 0
    dilated = ndi.binary_dilation(fg, iterations=1)
    restored = np.zeros_like(fg)
    n = 0
    px = 0
    objects = ndi.find_objects(labels)
    for cid, slc in enumerate(objects, start=1):
        if slc is None:
            continue
        ys, xs = slc
        comp = labels[ys, xs] == cid
        area = int(comp.sum())
        if area < p.restore_min_area or area > p.restore_max_area:
            continue
        y0, y1 = max(0, ys.start - 1), min(fg.shape[0], ys.stop + 1)
        x0, x1 = max(0, xs.start - 1), min(fg.shape[1], xs.stop + 1)
        if not bool(((labels[y0:y1, x0:x1] == cid) & dilated[y0:y1, x0:x1]).any()):
            continue
        med_l = float(np.median(luma[ys, xs][comp]))
        med_c = float(np.median(chroma[ys, xs][comp]))
        mean_d = float(dist[ys, xs][comp].mean())
        if not (
            med_c >= p.restore_min_chroma
            or med_l <= p.restore_max_luma
            or mean_d >= p.restore_min_dist
        ):
            continue
        restored[ys, xs] |= comp
        n += 1
        px += area
    return fg | restored, n, px


def decontam_rim(rgb: np.ndarray, fg: np.ndarray, width: int, luma_cap: float) -> np.ndarray:
    out = rgb.copy()
    if not fg.any():
        return out
    luma, chroma = luma_chroma(rgb)
    dist_in = ndi.distance_transform_edt(fg)
    fringe = fg & (dist_in <= width) & (luma >= 210) & (chroma <= 45)
    safe = fg & (dist_in >= width + 5) & ((chroma >= 10) | (luma <= 215))
    if not safe.any():
        safe = fg & (dist_in >= width + 5)
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
    mean, std = paper_model(rgb)
    luma, chroma = luma_chroma(rgb)
    dist = bg_distance(rgb, mean, std)

    paper = (luma >= p.paper_luma_min) & (chroma <= p.paper_chroma_max) & (dist <= p.paper_dist_max)
    outer_bg = border_connected(paper)
    enclosed = paper & ~outer_bg
    punched = punch_components(enclosed, p.hole_min_area)

    fg = ~(outer_bg | punched)
    fg, n_rest, px_rest = restore_paint(fg, punched, luma, chroma, dist, p)

    # Hard rim cut: near-white FG touching BG → transparent (kills white halo band)
    if p.rim_cut_px > 0:
        bg = ~fg
        near_white = fg & (luma >= p.rim_cut_luma) & (chroma <= p.rim_cut_chroma)
        rim = near_white & ndi.binary_dilation(bg, iterations=p.rim_cut_px)
        fg = fg & ~rim

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
        "outer_bg_px": int(outer_bg.sum()),
        "punched_px": int(punched.sum()),
        "restore_components": n_rest,
        "restore_px": px_rest,
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
    prev.save(path, quality=93)


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
    ap.add_argument("--rim-cut", type=int, default=3)
    ap.add_argument("--full-max", type=int, default=3600)
    args = ap.parse_args()
    p = Params(rim_cut_px=args.rim_cut)

    rgb_path = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    rgb = np.asarray(Image.open(rgb_path).convert("RGB"), dtype=np.uint8)
    rgba, metrics = run_pipeline(rgb, p)

    out_dir = REPO / "Images/candidates/image14-research/fusion-outer-v8"
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/USER_REVIEW"
    review.mkdir(parents=True, exist_ok=True)

    out_png = out_dir / f"14-outer-v8-r{p.rim_cut_px}-x4.png"
    Image.fromarray(rgba, "RGBA").save(out_png, optimize=True)
    (out_dir / f"{out_png.stem}-metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    gray = np.full(rgba.shape[:2] + (3,), 140, dtype=np.uint8)
    mag = np.zeros_like(gray)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    save_full(review / "15-outer-v8-full-gray.jpg", rgba, gray, args.full_max)
    save_full(review / "15-outer-v8-full-magenta.jpg", rgba, mag, args.full_max)
    h = rgba.shape[0]
    save_full(review / "15-outer-v8-upper-gray.jpg", rgba[: h // 2], gray[: h // 2], args.full_max)
    # mid coral band (where enclosed BG is densest)
    y0, y1 = h // 5, 3 * h // 5
    save_full(review / "15-outer-v8-mid-gray.jpg", rgba[y0:y1], gray[y0:y1], args.full_max)

    x8_w, x8_h = 7528, 13376
    sx, sy = rgb.shape[1] / x8_w, rgb.shape[0] / x8_h

    def sx8(x: int, y: int, ww: int, hh: int) -> tuple[int, int, int, int]:
        return int(x * sx), int(y * sy), max(1, int(ww * sx)), max(1, int(hh * sy))

    for name, box in [
        ("cut00", sx8(3601, 6253, 320, 400)),
        ("cut00_wide", sx8(3500, 6100, 520, 520)),
        ("enclosed_tri", sx8(6452 - 128, 5548 - 128, 256, 256)),
        ("fringe_pink", sx8(4355 - 128, 5013 - 128, 256, 256)),
    ]:
        make_review(review / f"15-outer-v8-{name}.jpg", rgba, *box, scale=3)

    drive = PRODUCT / "Images/candidates/image14-research/fusion-outer-v8"
    drive.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(drive / out_png.name, optimize=True)

    print(json.dumps({"out_png": str(out_png.resolve()), "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
