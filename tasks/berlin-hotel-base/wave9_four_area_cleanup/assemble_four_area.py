#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
BASE = Path("tasks/berlin-hotel-base/wave8_top_and_base_repair/results/v07_top_stone_tight_bottom.png")

CONTEXT_BOX = (2096, 1877, 4192, 3127)
RIGHT_HOTEL_GUARD = (3300, 880, 4192, 2450)
APPROVED_TOP_GUARD = (3300, 880, 4192, 1600)
STAIR_GUARD = (1720, 2200, 2600, 2940)
WATER_GUARD = (0, 3160, 4192, 3848)

REGIONS = {
    "r1_ghost_pillar": [(2216, 2462), (2413, 2477), (2436, 2872), (2216, 2879)],
    "r2_church_entrance": [(2436, 2037), (2906, 2044), (2952, 2538), (2451, 2591), (2345, 2363)],
    "r3_dirty_base": [(3096, 2522), (3407, 2538), (3430, 2917), (3096, 2932)],
    "r4_dirty_far_right": [(3476, 2606), (4068, 2614), (4098, 2940), (3483, 2947)],
}


def rel(poly: list[tuple[int, int]]) -> list[tuple[int, int]]:
    x0, y0, _, _ = CONTEXT_BOX
    return [(x - x0, y - y0) for x, y in poly]


def mask_for(names: list[str], feather: int) -> Image.Image:
    size = (CONTEXT_BOX[2] - CONTEXT_BOX[0], CONTEXT_BOX[3] - CONTEXT_BOX[1])
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for name in names:
        d.polygon(rel(REGIONS[name]), fill=255)
    if feather:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return m


def fit_context(path: Path) -> Image.Image:
    size = (CONTEXT_BOX[2] - CONTEXT_BOX[0], CONTEXT_BOX[3] - CONTEXT_BOX[1])
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def paste_context(base: Image.Image, donor: Image.Image, mask: Image.Image) -> Image.Image:
    out = base.copy()
    crop = out.crop(CONTEXT_BOX)
    patched = Image.composite(donor, crop, mask)
    out.paste(patched, CONTEXT_BOX[:2])
    return protect(out, base)


def protect(im: Image.Image, base: Image.Image) -> Image.Image:
    out = im.copy()
    for box in (RIGHT_HOTEL_GUARD, APPROVED_TOP_GUARD, STAIR_GUARD, WATER_GUARD):
        out.paste(base.crop(box), box[:2])
    return out


def save_variant(label: str, im: Image.Image) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / f"{label}.png"
    im.save(p)
    for name, pts in REGIONS.items():
        xs = [x for x, y in pts]
        ys = [y for x, y in pts]
        box = (max(0, min(xs) - 80), max(0, min(ys) - 80), min(im.size[0], max(xs) + 80), min(im.size[1], max(ys) + 80))
        im.crop(box).save(RESULTS / f"{label}_{name}_crop.png")
    im.crop(CONTEXT_BOX).save(RESULTS / f"{label}_context_crop.png")
    return p


def diff_count(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> int:
    aa = np.asarray(a.crop(box).convert("RGB"))
    bb = np.asarray(b.crop(box).convert("RGB"))
    return int((np.abs(aa.astype(int) - bb.astype(int)).max(axis=2) > 2).sum())


def make_board(items: list[tuple[str, Path]]) -> None:
    tile_w, tile_h = 760, 540
    board = Image.new("RGB", (tile_w * 2 + 30, tile_h * 2 + 40), "white")
    d = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items[:4]):
        im = Image.open(path).convert("RGB")
        crop = im.crop(CONTEXT_BOX).resize((720, 430), Image.Resampling.LANCZOS)
        x = 10 + (i % 2) * tile_w
        y = 10 + (i // 2) * tile_h
        d.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 32))
    board.save(RESULTS / "wave9_four_area_feedback_board.png")


def verify(items: list[tuple[str, Path]]) -> None:
    base = Image.open(BASE).convert("RGB")
    boxes = {
        "context": CONTEXT_BOX,
        "right_hotel_guard": RIGHT_HOTEL_GUARD,
        "top_guard": APPROVED_TOP_GUARD,
        "stair_guard": STAIR_GUARD,
        "water_guard": WATER_GUARD,
    }
    lines = []
    for label, path in items:
        im = Image.open(path).convert("RGB")
        parts = [label]
        for name, box in boxes.items():
            parts.append(f"{name}_changed={diff_count(base, im, box)}")
        parts.append(f"path={path.resolve()}")
        lines.append("\t".join(parts))
    (RESULTS / "wave9_four_area_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    base = Image.open(BASE).convert("RGB")
    raw = RAW / "four_area_openai_raw.png"
    items: list[tuple[str, Path]] = [("baseline", BASE)]
    if raw.exists():
        donor = fit_context(raw)
        all_mask = mask_for(list(REGIONS), 4)
        cleanup_mask = mask_for(["r1_ghost_pillar", "r3_dirty_base", "r4_dirty_far_right"], 5)
        church_mask = mask_for(["r2_church_entrance"], 3)
        hotel_mask = mask_for(["r3_dirty_base", "r4_dirty_far_right"], 4)
        items.append(("v01 all four tight", save_variant("v01_all_four_tight", paste_context(base, donor, all_mask))))
        items.append(("v02 cleanup only", save_variant("v02_cleanup_only_no_church", paste_context(base, donor, cleanup_mask))))
        items.append(("v03 church only", save_variant("v03_church_only", paste_context(base, donor, church_mask))))
        items.append(("v04 hotel dirt only", save_variant("v04_hotel_dirty_only", paste_context(base, donor, hotel_mask))))
    make_board(items)
    verify(items)


if __name__ == "__main__":
    main()
