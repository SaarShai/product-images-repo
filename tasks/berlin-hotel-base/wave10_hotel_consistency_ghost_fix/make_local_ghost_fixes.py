#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
BASE = RESULTS / "v01_hotel_consistency.png"
FALLBACK = Path("tasks/berlin-hotel-base/wave9_four_area_cleanup/results/v01_all_four_tight.png")
GHOST_BOX = (2140, 2350, 2525, 3005)

# Tight target around the visible pale vertical ghost, avoiding the turret.
UPPER = [(2226, 2475), (2328, 2490), (2330, 2758), (2220, 2760)]
LOWER = [(2222, 2762), (2298, 2762), (2298, 2882), (2220, 2886)]


def load_base() -> Image.Image:
    return Image.open(BASE if BASE.exists() else FALLBACK).convert("RGB")


def mask_full(size: tuple[int, int], polys: list[list[tuple[int, int]]]) -> np.ndarray:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon(p, fill=255)
    return np.asarray(m)


def save(label: str, arr_rgb: np.ndarray) -> Path:
    im = Image.fromarray(arr_rgb)
    p = RESULTS / f"{label}.png"
    im.save(p)
    im.crop(GHOST_BOX).save(RESULTS / f"{label}_ghost_crop.png")
    return p


def inpaint_variant(base: Image.Image) -> Path:
    arr = np.asarray(base)
    mask = mask_full(base.size, [UPPER, LOWER])
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    out = cv2.inpaint(bgr, mask, 7, cv2.INPAINT_TELEA)
    return save("v04_hotel_plus_ghost_inpaint", cv2.cvtColor(out, cv2.COLOR_BGR2RGB))


def clone_variant(base: Image.Image) -> Path:
    arr = np.asarray(base).copy()
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    # Clone neighboring foliage over the upper vertical haze.
    for target_box, source_shift in [
        ((2212, 2464, 2342, 2772), (-132, -8)),
        ((2208, 2750, 2310, 2898), (-118, 0)),
    ]:
        x0, y0, x1, y1 = target_box
        sx0, sy0, sx1, sy1 = x0 + source_shift[0], y0 + source_shift[1], x1 + source_shift[0], y1 + source_shift[1]
        src = bgr[sy0:sy1, sx0:sx1].copy()
        local_mask = np.zeros(src.shape[:2], dtype=np.uint8)
        cv2.rectangle(local_mask, (6, 6), (src.shape[1] - 7, src.shape[0] - 7), 255, -1)
        center = ((x0 + x1) // 2, (y0 + y1) // 2)
        bgr = cv2.seamlessClone(src, bgr, local_mask, center, cv2.NORMAL_CLONE)
    return save("v05_hotel_plus_ghost_seamless_clone", cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))


def diff_overlay(base: Image.Image, fixed_path: Path, out_path: Path) -> None:
    b = base.crop(GHOST_BOX)
    f = Image.open(fixed_path).convert("RGB").crop(GHOST_BOX)
    diff = ImageChops.difference(b, f).convert("L")
    arr = np.asarray(diff)
    heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    heat[..., 0] = np.clip(arr * 6, 0, 255)
    heat[..., 1] = np.clip(arr * 2, 0, 100)
    Image.blend(b, Image.fromarray(heat), 0.5).save(out_path)


def board(paths: list[Path]) -> None:
    base = load_base()
    items = [("hotel fix baseline", base)] + [(p.stem, Image.open(p).convert("RGB")) for p in paths]
    tile_w, tile_h = 390, 720
    out = Image.new("RGB", (tile_w * len(items) + 20, tile_h + 50), "white")
    d = ImageDraw.Draw(out)
    for i, (label, im) in enumerate(items):
        crop = im.crop(GHOST_BOX).resize((360, 620), Image.Resampling.LANCZOS)
        x = 10 + i * tile_w
        d.text((x, 10), label, fill=(140, 0, 0))
        out.paste(crop, (x, 40))
    out.save(RESULTS / "wave10_local_ghost_fix_board.png")
    if paths:
        diff_overlay(base, paths[-1], RESULTS / "wave10_local_ghost_diff_overlay.png")


def main() -> None:
    base = load_base()
    paths = [inpaint_variant(base), clone_variant(base)]
    board(paths)
    lines = []
    b = np.asarray(base.crop(GHOST_BOX).convert("RGB"))
    for p in paths:
        im = np.asarray(Image.open(p).convert("RGB").crop(GHOST_BOX))
        changed = int((np.abs(im.astype(int) - b.astype(int)).max(axis=2) > 2).sum())
        lines.append(f"{p.stem}\tghost_changed={changed}\tpath={p.resolve()}")
    (RESULTS / "wave10_local_ghost_verification.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
