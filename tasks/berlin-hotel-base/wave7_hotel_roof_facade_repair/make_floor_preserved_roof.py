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

# These masks deliberately keep the donor out of the window/floor grid. Earlier
# variants let the OpenAI donor dip below the roof line, which caused the top
# floors to warp. Coordinates are full-canvas pixels.
ROOF_CAP_STRICT = [
    (3445, 1200),
    (3488, 1164),
    (3488, 1085),
    (3658, 1070),
    (3695, 1132),
    (3775, 1142),
    (3812, 1215),
    (3782, 1262),
    (3515, 1268),
    (3452, 1242),
]

ROOF_CAP_WITH_LEDGE = [
    (3428, 1212),
    (3488, 1150),
    (3488, 1074),
    (3665, 1062),
    (3700, 1122),
    (3782, 1138),
    (3822, 1214),
    (3790, 1290),
    (3502, 1290),
    (3428, 1252),
]

ANTENNA_AND_CENTER_BLOCK = [
    (3638, 875),
    (3688, 875),
    (3698, 1260),
    (3615, 1260),
    (3618, 1110),
    (3638, 1110),
]

FACADE_RESTORE = [
    (3425, 1276),
    (3825, 1276),
    (3825, 1680),
    (3425, 1680),
]


def donor(raw: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(raw).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def poly_mask(size: tuple[int, int], polys: list[list[tuple[int, int]]], feather: int, opacity: float = 1.0) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for poly in polys:
        d.polygon(poly, fill=round(255 * opacity))
    if feather:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return m


def clamp_facade(mask: Image.Image, restore_start_y: int, transition: int) -> Image.Image:
    arr = np.asarray(mask).astype(np.float32)
    h, _ = arr.shape
    ramp = np.ones((h, 1), dtype=np.float32)
    y0 = restore_start_y
    y1 = restore_start_y + transition
    if transition > 0:
        ramp[y0:y1, 0] = np.linspace(1.0, 0.0, y1 - y0, endpoint=False)
    ramp[y1:, 0] = 0.0
    arr *= ramp
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L")


def restore_base_facade(out: Image.Image, base: Image.Image, feather: int = 5) -> Image.Image:
    restore = poly_mask(base.size, [FACADE_RESTORE], feather)
    return Image.composite(base, out, restore)


def diff_overlay(base_crop: Image.Image, crop: Image.Image, path: Path) -> None:
    diff = ImageChops.difference(base_crop, crop).convert("L")
    arr = np.asarray(diff)
    heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    heat[..., 0] = np.clip(arr * 5, 0, 255)
    heat[..., 1] = np.clip(arr * 2, 0, 120)
    Image.blend(base_crop, Image.fromarray(heat), 0.48).save(path)


def make_variant(
    name: str,
    raw_path: Path,
    polys: list[list[tuple[int, int]]],
    feather: int,
    restore_start_y: int,
    transition: int,
    hard_restore: bool,
) -> tuple[str, Path]:
    base = Image.open(BASE).convert("RGB")
    base_crop = base.crop(CROP_BOX)
    m = poly_mask(base.size, polys, feather)
    m = clamp_facade(m, restore_start_y, transition)
    out = Image.composite(donor(raw_path, base.size), base, m)
    if hard_restore:
        out = restore_base_facade(out, base)
    path = RESULTS / f"{name}.png"
    mask_path = RESULTS / f"{name}_mask.png"
    crop_path = RESULTS / f"{name}_crop.png"
    diff_path = RESULTS / f"{name}_diff_overlay_crop.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    out.save(path)
    m.crop(CROP_BOX).save(mask_path)
    out.crop(CROP_BOX).save(crop_path)
    diff_overlay(base_crop, out.crop(CROP_BOX), diff_path)
    return name, path


def make_board(items: list[tuple[str, Path]]) -> None:
    tile_w, tile_h = 590, 730
    cols = 2
    rows = (len(items) + 1) // 2
    board = Image.new("RGB", (cols * tile_w + 30, rows * tile_h + 20), "white")
    draw = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items):
        im = Image.open(path).convert("RGB")
        crop = im.crop(CROP_BOX).resize((560, 694), Image.Resampling.LANCZOS)
        x = 10 + (i % cols) * tile_w
        y = 10 + (i // cols) * tile_h
        draw.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 30))
    board.save(RESULTS / "hotel_roof_facade_floor_preserved_board.png")


def verify(variants: list[tuple[str, Path]]) -> None:
    base = np.asarray(Image.open(BASE).convert("RGB"))
    facade = np.zeros(base.shape[:2], dtype=bool)
    # Window/floor preservation zone in the hotel crop.
    facade[1276:1680, 3425:3825] = True
    stair = np.zeros(base.shape[:2], dtype=bool)
    sx0, sy0, sx1, sy1 = STAIR_PROTECTED
    stair[sy0:sy1, sx0:sx1] = True
    lines = []
    for label, path in variants:
        im = np.asarray(Image.open(path).convert("RGB"))
        diff = np.abs(im.astype(int) - base.astype(int)).max(axis=2) > 2
        lines.append(
            f"{label}\tchanged_total={int(diff.sum())}"
            f"\tfacade_restore_zone_changed={int((diff & facade).sum())}"
            f"\tstair_protected_changed={int((diff & stair).sum())}"
            f"\tpath={path.resolve()}"
        )
    (RESULTS / "hotel_roof_facade_floor_preserved_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    variants = [
        make_variant(
            "v07_loose_roof_cap_strict_facade_restored",
            RAW / "reference_guided_top_loose_raw.png",
            [ROOF_CAP_STRICT, ANTENNA_AND_CENTER_BLOCK],
            feather=8,
            restore_start_y=1248,
            transition=34,
            hard_restore=True,
        ),
        make_variant(
            "v08_loose_roof_cap_ledge_facade_restored",
            RAW / "reference_guided_top_loose_raw.png",
            [ROOF_CAP_WITH_LEDGE, ANTENNA_AND_CENTER_BLOCK],
            feather=7,
            restore_start_y=1260,
            transition=28,
            hard_restore=True,
        ),
        make_variant(
            "v09_precise_roof_cap_strict_facade_restored",
            RAW / "reference_guided_top_precise_raw.png",
            [ROOF_CAP_STRICT, ANTENNA_AND_CENTER_BLOCK],
            feather=8,
            restore_start_y=1248,
            transition=34,
            hard_restore=True,
        ),
        make_variant(
            "v10_precise_roof_cap_ledge_facade_restored",
            RAW / "reference_guided_top_precise_raw.png",
            [ROOF_CAP_WITH_LEDGE, ANTENNA_AND_CENTER_BLOCK],
            feather=7,
            restore_start_y=1260,
            transition=28,
            hard_restore=True,
        ),
    ]
    board_items = [
        ("base / floors to preserve", BASE),
        ("old best donor / distorts floors", RESULTS / "reference_guided_top_loose_masked.png"),
        *variants,
    ]
    make_board(board_items)
    verify(variants)


if __name__ == "__main__":
    main()
