#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
BASE = Path("tasks/berlin-hotel-base/wave6_bridge_stairs_openai_donor/results/stair_architecture_under_foliage_masked.png")
CROP_BOX = (3350, 950, 3940, 1680)
STAIR_PROTECTED = (1720, 2200, 2600, 2940)

# Final masks are tighter than the generation mask. The raw OpenAI donor had
# enough context to understand the reference; these keep only the useful roof
# and upper facade pixels.
ROOF_TOP_POLY = [(3485, 1065), (3760, 1060), (3770, 1392), (3522, 1422), (3458, 1300)]
ROOF_PLUS_TOP_WINDOWS_POLY = [(3482, 1065), (3762, 1060), (3772, 1462), (3538, 1492), (3454, 1365)]


def mask(size: tuple[int, int], poly: list[tuple[int, int]], feather: int = 16, opacity: float = 1.0) -> Image.Image:
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
    recipes = [
        ("v03_loose_roof_top_only", RAW / "reference_guided_top_loose_raw.png", ROOF_TOP_POLY, 14, 1.0),
        ("v04_loose_roof_plus_top_windows", RAW / "reference_guided_top_loose_raw.png", ROOF_PLUS_TOP_WINDOWS_POLY, 16, 0.92),
        ("v05_precise_roof_top_only", RAW / "reference_guided_top_precise_raw.png", ROOF_TOP_POLY, 14, 1.0),
        ("v06_precise_roof_plus_top_windows", RAW / "reference_guided_top_precise_raw.png", ROOF_PLUS_TOP_WINDOWS_POLY, 16, 0.92),
    ]
    variants: list[tuple[str, Path]] = []
    for name, raw, poly, feather, opacity in recipes:
        if not raw.exists():
            continue
        out = Image.composite(donor(raw, base.size), base, mask(base.size, poly, feather, opacity))
        path = RESULTS / f"{name}.png"
        out.save(path)
        out.crop(CROP_BOX).save(RESULTS / f"{name}_crop.png")
        diff_overlay(base_crop, out.crop(CROP_BOX), RESULTS / f"{name}_diff_overlay_crop.png")
        variants.append((name, path))

    items = [
        ("base", BASE),
        ("v01 loose full mask", RESULTS / "reference_guided_top_loose_masked.png"),
        ("v02 precise full mask", RESULTS / "reference_guided_top_precise_masked.png"),
        *variants,
    ]
    tile_w, tile_h = 590, 730
    cols = 2
    rows = (len(items) + 1) // 2
    board = Image.new("RGB", (cols * tile_w + 30, rows * tile_h + 20), "white")
    draw = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items):
        if not Path(path).exists():
            continue
        im = Image.open(path).convert("RGB")
        crop = im.crop(CROP_BOX).resize((560, 694), Image.Resampling.LANCZOS)
        x = 10 + (i % cols) * tile_w
        y = 10 + (i // 2) * tile_h
        draw.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 30))
    board.save(RESULTS / "hotel_roof_facade_reference_tight_board.png")

    base_arr = np.asarray(base)
    hard = np.asarray(mask(base.size, ROOF_PLUS_TOP_WINDOWS_POLY, 2)) > 0
    stair = np.zeros(base_arr.shape[:2], dtype=bool)
    sx0, sy0, sx1, sy1 = STAIR_PROTECTED
    stair[sy0:sy1, sx0:sx1] = True
    lines = []
    for label, path in variants:
        im = np.asarray(Image.open(path).convert("RGB"))
        diff = np.abs(im.astype(int) - base_arr.astype(int)).max(axis=2) > 2
        lines.append(
            f"{label}\tinside_changed={int((diff & hard).sum())}"
            f"\toutside_changed={int((diff & ~hard).sum())}"
            f"\tstair_protected_changed={int((diff & stair).sum())}"
            f"\tpath={path.resolve()}"
        )
    (RESULTS / "hotel_roof_facade_reference_tight_verification.txt").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
