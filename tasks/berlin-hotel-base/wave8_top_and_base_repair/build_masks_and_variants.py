#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
for p in (INPUTS, RAW, RESULTS):
    p.mkdir(parents=True, exist_ok=True)

BASE = Path("tasks/berlin-hotel-base/wave7_hotel_roof_facade_repair/results/v11_right_parapet_precise_reinforced.png")
STAIR_PROTECTED = (1720, 2200, 2600, 2940)
FLOOR_GUARD = (3350, 1340, 3895, 2440)

TOP_CONTEXT = (3480, 950, 4192, 1540)
BOTTOM_CONTEXT = (3650, 2400, 4192, 3340)
RIGHT_CONTEXT = (3220, 880, 4192, 3340)

TOP_GEN_POLY = [
    (3770, 1035),
    (4050, 1100),
    (4188, 1280),
    (4188, 1460),
    (3960, 1365),
    (3788, 1240),
]
TOP_BLEND_POLY = [
    (3810, 1100),
    (4040, 1162),
    (4188, 1300),
    (4188, 1438),
    (3972, 1350),
    (3820, 1248),
]
BOTTOM_GEN_POLY = [
    (3910, 2470),
    (4191, 2470),
    (4191, 3230),
    (3960, 3240),
    (3900, 2920),
]
BOTTOM_BLEND_POLY = [
    (3925, 2540),
    (4191, 2540),
    (4191, 3185),
    (3975, 3188),
    (3920, 2910),
]


def polygon_mask(size: tuple[int, int], polys: list[list[tuple[int, int]]], feather: int) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for poly in polys:
        d.polygon(poly, fill=255)
    if feather:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return m


def save_inputs() -> None:
    base = Image.open(BASE).convert("RGB")
    base.save(INPUTS / "current_baseline_v11.png")
    gen = polygon_mask(base.size, [TOP_GEN_POLY, BOTTOM_GEN_POLY], 12)
    gen.save(INPUTS / "quick_top_base_gen_mask.png")
    overlay = base.copy()
    d = ImageDraw.Draw(overlay, "RGBA")
    d.polygon(TOP_GEN_POLY, fill=(120, 220, 40, 70), outline=(40, 180, 20, 255))
    d.polygon(BOTTOM_GEN_POLY, fill=(120, 220, 40, 70), outline=(40, 180, 20, 255))
    overlay.crop(RIGHT_CONTEXT).save(INPUTS / "quick_top_base_mask_overlay_context.png")
    for name, box in [
        ("top_issue_context", TOP_CONTEXT),
        ("bottom_issue_context", BOTTOM_CONTEXT),
        ("right_building_context", RIGHT_CONTEXT),
    ]:
        base.crop(box).save(INPUTS / f"{name}.png")


def fit(path: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def protect(mask: Image.Image) -> Image.Image:
    arr = np.asarray(mask).copy()
    x0, y0, x1, y1 = FLOOR_GUARD
    arr[y0:y1, x0:x1] = 0
    sx0, sy0, sx1, sy1 = STAIR_PROTECTED
    arr[sy0:sy1, sx0:sx1] = 0
    return Image.fromarray(arr, "L")


def diff_count(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> int:
    aa = np.asarray(a.crop(box).convert("RGB"))
    bb = np.asarray(b.crop(box).convert("RGB"))
    return int((np.abs(aa.astype(int) - bb.astype(int)).max(axis=2) > 2).sum())


def save_variant(label: str, im: Image.Image) -> Path:
    p = RESULTS / f"{label}.png"
    im.save(p)
    im.crop(TOP_CONTEXT).save(RESULTS / f"{label}_top_crop.png")
    im.crop(BOTTOM_CONTEXT).save(RESULTS / f"{label}_bottom_crop.png")
    return p


def make_board(items: list[tuple[str, Path]]) -> None:
    base_size = Image.open(BASE).size
    tile_w, tile_h = 760, 900
    board = Image.new("RGB", (tile_w * 2 + 30, tile_h * 2 + 40), "white")
    d = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items[:4]):
        im = fit(path, base_size)
        crop = im.crop(RIGHT_CONTEXT).resize((720, 820), Image.Resampling.LANCZOS)
        x = 10 + (i % 2) * tile_w
        y = 10 + (i // 2) * tile_h
        d.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 32))
    board.save(RESULTS / "wave8_top_base_feedback_board.png")


def verify(items: list[tuple[str, Path]]) -> None:
    base = Image.open(BASE).convert("RGB")
    lines = []
    for label, path in items:
        im = fit(path, base.size)
        lines.append(
            f"{label}"
            f"\ttop_changed={diff_count(base, im, TOP_CONTEXT)}"
            f"\tbottom_changed={diff_count(base, im, BOTTOM_CONTEXT)}"
            f"\tfloor_guard_changed={diff_count(base, im, FLOOR_GUARD)}"
            f"\tstair_guard_changed={diff_count(base, im, STAIR_PROTECTED)}"
            f"\tpath={path.resolve()}"
        )
    (RESULTS / "wave8_top_base_verification.txt").write_text("\n".join(lines) + "\n")


def assemble() -> None:
    base = Image.open(BASE).convert("RGB")
    donor_candidates = sorted(RAW.glob("*_raw.png"))
    top_mask = protect(polygon_mask(base.size, [TOP_BLEND_POLY], 2))
    top_tight = protect(polygon_mask(base.size, [TOP_BLEND_POLY], 0))
    bottom_mask = protect(polygon_mask(base.size, [BOTTOM_BLEND_POLY], 4))
    both_mask = ImageChops.lighter(top_mask, bottom_mask)
    both_tight_top = ImageChops.lighter(top_tight, bottom_mask)

    items: list[tuple[str, Path]] = [("current v11 baseline", BASE)]

    for idx, raw in enumerate(donor_candidates, 1):
        donor = fit(raw, base.size)
        top_only = Image.composite(donor, base, top_mask)
        bottom_only = Image.composite(donor, base, bottom_mask)
        both = Image.composite(donor, base, both_mask)
        tight_top = Image.composite(donor, base, both_tight_top)
        items.extend(
            [
                (f"v{idx:02d}a OpenAI top only", save_variant(f"v{idx:02d}a_openai_top_only", top_only)),
                (f"v{idx:02d}b OpenAI bottom only", save_variant(f"v{idx:02d}b_openai_bottom_only", bottom_only)),
                (f"v{idx:02d}c OpenAI top+bottom", save_variant(f"v{idx:02d}c_openai_top_bottom", both)),
                (f"v{idx:02d}d OpenAI tight top+bottom", save_variant(f"v{idx:02d}d_openai_tight_top_bottom", tight_top)),
            ]
        )

    make_board(items)
    verify(items)


def main() -> None:
    save_inputs()
    assemble()


if __name__ == "__main__":
    main()
