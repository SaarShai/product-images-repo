#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
BASE = Path("tasks/berlin-hotel-base/wave7_hotel_roof_facade_repair/results/v11_right_parapet_precise_reinforced.png")

TOP_BOX = (3480, 950, 4192, 1540)
BOTTOM_BOX = (3650, 2400, 4192, 3340)
RIGHT_CONTEXT = (3220, 880, 4192, 3340)
FLOOR_GUARD = (3350, 1340, 3895, 2440)
STAIR_PROTECTED = (1720, 2200, 2600, 2940)

TOP_POLY_ABS = [
    (3795, 1068),
    (4191, 1162),
    (4191, 1452),
    (3978, 1358),
    (3805, 1248),
]
BOTTOM_POLY_ABS = [
    (3900, 2480),
    (4191, 2480),
    (4191, 3225),
    (3970, 3235),
    (3905, 2935),
]
BOTTOM_TIGHT_POLY_ABS = [
    (3975, 2500),
    (4191, 2500),
    (4191, 3040),
    (3995, 3048),
    (3945, 2908),
    (3958, 2640),
]


def rel_poly(poly: list[tuple[int, int]], box: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    x0, y0, _, _ = box
    return [(x - x0, y - y0) for x, y in poly]


def mask(size: tuple[int, int], poly: list[tuple[int, int]], feather: int) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.polygon(poly, fill=255)
    if feather:
        m = m.filter(ImageFilter.GaussianBlur(feather))
    return m


def save_inputs() -> None:
    base = Image.open(BASE).convert("RGB")
    for p in (INPUTS, RAW, RESULTS):
        p.mkdir(parents=True, exist_ok=True)
    top = base.crop(TOP_BOX)
    bottom = base.crop(BOTTOM_BOX)
    top.save(INPUTS / "top_crop_source.png")
    bottom.save(INPUTS / "bottom_crop_source.png")
    mask(top.size, rel_poly(TOP_POLY_ABS, TOP_BOX), 8).save(INPUTS / "top_crop_mask.png")
    mask(bottom.size, rel_poly(BOTTOM_POLY_ABS, BOTTOM_BOX), 10).save(INPUTS / "bottom_crop_mask.png")
    overlay = base.copy()
    d = ImageDraw.Draw(overlay, "RGBA")
    d.polygon(TOP_POLY_ABS, fill=(120, 220, 40, 70), outline=(40, 180, 20, 255))
    d.polygon(BOTTOM_POLY_ABS, fill=(120, 220, 40, 70), outline=(40, 180, 20, 255))
    d.polygon(BOTTOM_TIGHT_POLY_ABS, fill=(40, 130, 255, 45), outline=(20, 80, 220, 255))
    overlay.crop(RIGHT_CONTEXT).save(INPUTS / "crop_repair_overlay_context.png")


def fit_crop(path: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def paste_crop(base: Image.Image, donor_path: Path, box: tuple[int, int, int, int], blend_mask: Image.Image) -> Image.Image:
    donor = fit_crop(donor_path, (box[2] - box[0], box[3] - box[1]))
    out = base.copy()
    crop = out.crop(box)
    patched = Image.composite(donor, crop, blend_mask)
    out.paste(patched, (box[0], box[1]))
    return out


def top_stone_mask(donor_path: Path) -> Image.Image:
    size = (TOP_BOX[2] - TOP_BOX[0], TOP_BOX[3] - TOP_BOX[1])
    donor = fit_crop(donor_path, size)
    gate = np.asarray(mask(size, rel_poly(TOP_POLY_ABS, TOP_BOX), 0)) > 0
    arr = np.asarray(donor.convert("RGB"))
    r = arr[..., 0].astype(int)
    g = arr[..., 1].astype(int)
    b = arr[..., 2].astype(int)
    # Select pale limestone/parapet pixels from the donor while rejecting blue sky.
    stone = (r > 148) & (g > 132) & (b < 222) & ((r - b) > -12) & gate
    out = np.zeros(stone.shape, dtype=np.uint8)
    out[stone] = 255
    im = Image.fromarray(out, "L").filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(2))
    return im


def protect_full(im: Image.Image, base: Image.Image) -> Image.Image:
    out = im.copy()
    for box in (FLOOR_GUARD, STAIR_PROTECTED):
        out.paste(base.crop(box), (box[0], box[1]))
    return out


def save_variant(label: str, im: Image.Image) -> Path:
    p = RESULTS / f"{label}.png"
    im.save(p)
    im.crop(TOP_BOX).save(RESULTS / f"{label}_top_crop.png")
    im.crop(BOTTOM_BOX).save(RESULTS / f"{label}_bottom_crop.png")
    return p


def diff_count(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> int:
    aa = np.asarray(a.crop(box).convert("RGB"))
    bb = np.asarray(b.crop(box).convert("RGB"))
    return int((np.abs(aa.astype(int) - bb.astype(int)).max(axis=2) > 2).sum())


def make_board(items: list[tuple[str, Path]]) -> None:
    size = Image.open(BASE).size
    tile_w, tile_h = 760, 900
    board = Image.new("RGB", (tile_w * 2 + 30, tile_h * 2 + 40), "white")
    d = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items[:4]):
        im = Image.open(path).convert("RGB")
        if im.size != size:
            im = im.resize(size, Image.Resampling.LANCZOS)
        crop = im.crop(RIGHT_CONTEXT).resize((720, 820), Image.Resampling.LANCZOS)
        x = 10 + (i % 2) * tile_w
        y = 10 + (i // 2) * tile_h
        d.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 32))
    board.save(RESULTS / "wave8_crop_repair_feedback_board.png")


def verify(items: list[tuple[str, Path]]) -> None:
    base = Image.open(BASE).convert("RGB")
    lines = []
    for label, path in items:
        im = Image.open(path).convert("RGB")
        lines.append(
            f"{label}"
            f"\ttop_changed={diff_count(base, im, TOP_BOX)}"
            f"\tbottom_changed={diff_count(base, im, BOTTOM_BOX)}"
            f"\tfloor_guard_changed={diff_count(base, im, FLOOR_GUARD)}"
            f"\tstair_guard_changed={diff_count(base, im, STAIR_PROTECTED)}"
            f"\tpath={path.resolve()}"
        )
    (RESULTS / "wave8_crop_repair_verification.txt").write_text("\n".join(lines) + "\n")


def assemble() -> None:
    base = Image.open(BASE).convert("RGB")
    top_mask = mask((TOP_BOX[2] - TOP_BOX[0], TOP_BOX[3] - TOP_BOX[1]), rel_poly(TOP_POLY_ABS, TOP_BOX), 3)
    bottom_mask = mask((BOTTOM_BOX[2] - BOTTOM_BOX[0], BOTTOM_BOX[3] - BOTTOM_BOX[1]), rel_poly(BOTTOM_POLY_ABS, BOTTOM_BOX), 5)
    bottom_tight_mask = mask(
        (BOTTOM_BOX[2] - BOTTOM_BOX[0], BOTTOM_BOX[3] - BOTTOM_BOX[1]),
        rel_poly(BOTTOM_TIGHT_POLY_ABS, BOTTOM_BOX),
        10,
    )

    items: list[tuple[str, Path]] = [("baseline", BASE)]
    top_raw = RAW / "top_crop_openai_raw.png"
    bottom_raw = RAW / "bottom_crop_openai_raw.png"

    current = base.copy()
    if top_raw.exists():
        top_only = protect_full(paste_crop(base, top_raw, TOP_BOX, top_mask), base)
        items.append(("v01 top crop donor", save_variant("v01_top_crop_donor", top_only)))
        current = top_only
        top_stone = protect_full(paste_crop(base, top_raw, TOP_BOX, top_stone_mask(top_raw)), base)
        items.append(("v06 top stone-only donor", save_variant("v06_top_stone_only_donor", top_stone)))
    if bottom_raw.exists():
        bottom_only = protect_full(paste_crop(base, bottom_raw, BOTTOM_BOX, bottom_mask), base)
        items.append(("v02 bottom crop donor", save_variant("v02_bottom_crop_donor", bottom_only)))
        combined = protect_full(paste_crop(current, bottom_raw, BOTTOM_BOX, bottom_mask), base)
        items.append(("v03 combined top+bottom", save_variant("v03_combined_top_bottom_crop_donors", combined)))
        bottom_tight = protect_full(paste_crop(base, bottom_raw, BOTTOM_BOX, bottom_tight_mask), base)
        items.append(("v04 bottom tight donor", save_variant("v04_bottom_tight_crop_donor", bottom_tight)))
        combined_tight = protect_full(paste_crop(current, bottom_raw, BOTTOM_BOX, bottom_tight_mask), base)
        items.append(("v05 combined top+tight bottom", save_variant("v05_combined_top_tight_bottom_crop_donors", combined_tight)))
        if top_raw.exists():
            top_stone_current = protect_full(paste_crop(base, top_raw, TOP_BOX, top_stone_mask(top_raw)), base)
            combined_stone_tight = protect_full(paste_crop(top_stone_current, bottom_raw, BOTTOM_BOX, bottom_tight_mask), base)
            items.append(("v07 top stone+tight bottom", save_variant("v07_top_stone_tight_bottom", combined_stone_tight)))

    board_items = [items[0]]
    by_label = {label: (label, path) for label, path in items}
    for label in ("v06 top stone-only donor", "v04 bottom tight donor", "v07 top stone+tight bottom"):
        if label in by_label:
            board_items.append(by_label[label])
    make_board(board_items)
    verify(items)


def main() -> None:
    save_inputs()
    assemble()


if __name__ == "__main__":
    main()
