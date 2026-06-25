#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
RESULTS = ROOT / "results"

BASE = Path("tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png")
CROP_BOX = (1720, 2200, 2600, 2940)

# Tighter final donor mask: broad enough to include the stair continuation and
# foreground tree occlusion, but low enough to avoid rewriting upper architecture.
TIGHT_POLY = [(1848, 2468), (2408, 2448), (2402, 2738), (1998, 2770), (1805, 2630)]
LOW_POLY = [(1850, 2535), (2375, 2508), (2380, 2725), (2005, 2760), (1820, 2648)]


def mask(size: tuple[int, int], poly: list[tuple[int, int]], feather: int, opacity: float = 1.0) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.polygon(poly, fill=round(255 * opacity))
    return m.filter(ImageFilter.GaussianBlur(feather))


def donor(raw: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(raw).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def diff_overlay(base_crop: Image.Image, crop: Image.Image, path: Path) -> None:
    diff = ImageChops.difference(base_crop, crop).convert("L")
    arr = np.asarray(diff)
    heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    heat[..., 0] = np.clip(arr * 5, 0, 255)
    heat[..., 1] = np.clip(arr * 2, 0, 120)
    Image.blend(base_crop, Image.fromarray(heat), 0.48).save(path)


def main() -> None:
    base = Image.open(BASE).convert("RGB")
    base_crop = base.crop(CROP_BOX)
    variants = []
    recipes = [
        ("v03_precise_tight_finalmask", RAW / "stair_continuation_precise_raw.png", TIGHT_POLY, 16, 1.0),
        ("v04_precise_low_finalmask", RAW / "stair_continuation_precise_raw.png", LOW_POLY, 12, 1.0),
        ("v05_foliage_tight_finalmask", RAW / "stair_architecture_under_foliage_raw.png", TIGHT_POLY, 16, 1.0),
        ("v06_foliage_low_softalpha", RAW / "stair_architecture_under_foliage_raw.png", LOW_POLY, 16, 0.78),
    ]
    for name, raw_path, poly, feather, opacity in recipes:
        if not raw_path.exists():
            continue
        out = Image.composite(donor(raw_path, base.size), base, mask(base.size, poly, feather, opacity))
        out_path = RESULTS / f"{name}.png"
        out.save(out_path)
        out.crop(CROP_BOX).save(RESULTS / f"{name}_crop.png")
        diff_overlay(base_crop, out.crop(CROP_BOX), RESULTS / f"{name}_diff_overlay_crop.png")
        variants.append((name, out_path))

    # Board.
    items = [("base", BASE), *variants]
    tile_w, tile_h = 704, 632
    cols = 2
    rows = (len(items) + 1) // 2
    board = Image.new("RGB", (cols * tile_w + 30, rows * tile_h + 20), "white")
    draw = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items):
        im = Image.open(path).convert("RGB")
        crop = im.crop(CROP_BOX).resize((704, 592), Image.Resampling.LANCZOS)
        x = 10 + (i % cols) * (tile_w + 10)
        y = 10 + (i // cols) * tile_h
        draw.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 30))
    board.save(RESULTS / "bridge_stairs_openai_tight_hybrid_board.png")

    hard = np.asarray(mask(base.size, TIGHT_POLY, 2)) > 0
    base_arr = np.asarray(base)
    lines = []
    for label, path in variants:
        im = np.asarray(Image.open(path).convert("RGB"))
        diff = np.abs(im.astype(int) - base_arr.astype(int)).max(axis=2) > 2
        lines.append(f"{label}\tinside_changed={int((diff & hard).sum())}\toutside_changed={int((diff & ~hard).sum())}\tpath={path.resolve()}")
    (RESULTS / "bridge_stairs_openai_tight_hybrid_verification.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
