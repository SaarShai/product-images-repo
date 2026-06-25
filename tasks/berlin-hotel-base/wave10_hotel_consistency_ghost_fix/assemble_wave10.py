#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
BASE = INPUTS / "baseline_wave9_v01.png"

HOTEL_BOX = (2860, 720, 4192, 3140)
GHOST_BOX = (2140, 2350, 2525, 3005)
TOP_GUARD = (3300, 720, 4192, 1050)
CHURCH_ENTRANCE_GUARD = (2320, 1960, 3020, 2680)
WATER_GUARD = (0, 3160, 4192, 3848)
STAIR_GUARD = (1720, 2200, 2600, 2940)


def fit(path: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def paste_crop(base: Image.Image, donor_path: Path, crop_box: tuple[int, int, int, int], mask_path: Path) -> Image.Image:
    donor = fit(donor_path, (crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]))
    mask = Image.open(mask_path).convert("L")
    crop = base.crop(crop_box)
    patched = Image.composite(donor, crop, mask)
    out = base.copy()
    out.paste(patched, crop_box[:2])
    return out


def protect(
    im: Image.Image,
    base: Image.Image,
    protect_church: bool = True,
    protect_stair: bool = True,
) -> Image.Image:
    out = im.copy()
    for box in (TOP_GUARD, WATER_GUARD):
        out.paste(base.crop(box), box[:2])
    if protect_stair:
        out.paste(base.crop(STAIR_GUARD), STAIR_GUARD[:2])
    if protect_church:
        out.paste(base.crop(CHURCH_ENTRANCE_GUARD), CHURCH_ENTRANCE_GUARD[:2])
    return out


def save(label: str, im: Image.Image) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / f"{label}.png"
    im.save(p)
    im.crop(HOTEL_BOX).save(RESULTS / f"{label}_hotel_crop.png")
    im.crop(GHOST_BOX).save(RESULTS / f"{label}_ghost_crop.png")
    return p


def diff_count(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> int:
    aa = np.asarray(a.crop(box).convert("RGB"))
    bb = np.asarray(b.crop(box).convert("RGB"))
    return int((np.abs(aa.astype(int) - bb.astype(int)).max(axis=2) > 2).sum())


def diff_overlay(base_crop: Image.Image, fixed_crop: Image.Image, path: Path) -> None:
    diff = ImageChops.difference(base_crop, fixed_crop).convert("L")
    arr = np.asarray(diff)
    heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    heat[..., 0] = np.clip(arr * 6, 0, 255)
    heat[..., 1] = np.clip(arr * 2, 0, 110)
    Image.blend(base_crop, Image.fromarray(heat), 0.5).save(path)


def make_board(items: list[tuple[str, Path]]) -> None:
    tile_w, tile_h = 720, 760
    board = Image.new("RGB", (tile_w * 2 + 30, tile_h * 2 + 40), "white")
    d = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items[:4]):
        im = Image.open(path).convert("RGB")
        crop = im.crop((2050, 700, 4192, 3140)).resize((680, 690), Image.Resampling.LANCZOS)
        x = 10 + (i % 2) * tile_w
        y = 10 + (i // 2) * tile_h
        d.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 32))
    board.save(RESULTS / "wave10_feedback_board.png")


def make_ghost_compare(base: Image.Image, fixed: Image.Image, path: Path) -> None:
    b = base.crop(GHOST_BOX)
    f = fixed.crop(GHOST_BOX)
    diff_path = RESULTS / "ghost_diff_overlay.png"
    diff_overlay(b, f, diff_path)
    board = Image.new("RGB", (1180, 760), "white")
    d = ImageDraw.Draw(board)
    for label, im, x in [("before", b, 10), ("after", f, 400), ("diff overlay", Image.open(diff_path), 790)]:
        d.text((x, 10), label, fill=(140, 0, 0))
        c = im.copy()
        c = c.resize((360, 680), Image.Resampling.LANCZOS)
        board.paste(c, (x, 40))
    board.save(path)


def verify(items: list[tuple[str, Path]]) -> None:
    base = Image.open(BASE).convert("RGB")
    boxes = {
        "hotel": HOTEL_BOX,
        "ghost": GHOST_BOX,
        "top_guard": TOP_GUARD,
        "church_guard": CHURCH_ENTRANCE_GUARD,
        "water_guard": WATER_GUARD,
        "stair_guard": STAIR_GUARD,
    }
    lines = []
    for label, path in items:
        im = Image.open(path).convert("RGB")
        parts = [label]
        for name, box in boxes.items():
            parts.append(f"{name}_changed={diff_count(base, im, box)}")
        parts.append(f"path={path.resolve()}")
        lines.append("\t".join(parts))
    (RESULTS / "wave10_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    base = Image.open(BASE).convert("RGB")
    items: list[tuple[str, Path]] = [("wave9 v01 baseline", BASE)]
    hotel_raw = RAW / "hotel_facade_consistency_raw.png"
    ghost_raw = RAW / "ghost_pillar_cleanup_raw.png"

    hotel_im = None
    if hotel_raw.exists():
        hotel_im = protect(
            paste_crop(base, hotel_raw, HOTEL_BOX, INPUTS / "hotel_facade_mask.png"),
            base,
            protect_church=True,
        )
        items.append(("v01 hotel consistency", save("v01_hotel_consistency", hotel_im)))

    ghost_im = None
    if ghost_raw.exists():
        ghost_im = protect(
            paste_crop(base, ghost_raw, GHOST_BOX, INPUTS / "ghost_pillar_mask.png"),
            base,
            protect_church=True,
            protect_stair=False,
        )
        items.append(("v02 ghost cleanup", save("v02_ghost_cleanup", ghost_im)))

    if hotel_im is not None and ghost_raw.exists():
        combined = protect(
            paste_crop(hotel_im, ghost_raw, GHOST_BOX, INPUTS / "ghost_pillar_mask.png"),
            base,
            protect_church=True,
            protect_stair=False,
        )
        items.append(("v03 hotel plus ghost", save("v03_hotel_plus_ghost", combined)))
        make_ghost_compare(base, combined, RESULTS / "wave10_ghost_before_after_diff.png")
    elif ghost_im is not None:
        make_ghost_compare(base, ghost_im, RESULTS / "wave10_ghost_before_after_diff.png")

    make_board(items)
    verify(items)


if __name__ == "__main__":
    main()
