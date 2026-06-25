#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
BASE = INPUTS / "baseline_hotel_consistency.png"
CTX_BOX = (2020, 2260, 2700, 3040)
GHOST_DETAIL = (2140, 2350, 2525, 3005)
HOTEL_GUARD = (2860, 720, 4192, 3140)
CHURCH_GUARD = (2320, 1960, 3020, 2680)
WATER_GUARD = (0, 3160, 4192, 3848)


def fit(path: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def paste_context(base: Image.Image, raw: Path, mask_path: Path, feather_extra: int = 0) -> Image.Image:
    donor = fit(raw, (CTX_BOX[2] - CTX_BOX[0], CTX_BOX[3] - CTX_BOX[1]))
    mask = Image.open(mask_path).convert("L")
    if feather_extra:
        mask = mask.filter(ImageFilter.GaussianBlur(feather_extra))
    crop = base.crop(CTX_BOX)
    patched = Image.composite(donor, crop, mask)
    out = base.copy()
    out.paste(patched, CTX_BOX[:2])
    # Preserve areas unrelated to the ghost repair.
    for box in (HOTEL_GUARD, WATER_GUARD):
        out.paste(base.crop(box), box[:2])
    # Preserve church entrance only; the ghost crop is lower/left of it.
    out.paste(base.crop(CHURCH_GUARD), CHURCH_GUARD[:2])
    return out


def local_control(base: Image.Image) -> Image.Image:
    # Conservative baseline-control: reduce the pale vertical haze by blending in
    # nearby left foliage/brick texture without generating new object geometry.
    arr = np.asarray(base).copy()
    out = base.copy()
    patch = base.crop((2050, 2380, 2200, 2925)).resize((155, 545), Image.Resampling.BICUBIC)
    m = Image.new("L", base.size, 0)
    d = ImageDraw.Draw(m)
    d.polygon([(2205, 2448), (2354, 2478), (2358, 2902), (2210, 2908)], fill=178)
    m = m.filter(ImageFilter.GaussianBlur(10))
    donor = Image.new("RGB", base.size)
    donor.paste(patch, (2205, 2370))
    return Image.composite(donor, out, m)


def save(label: str, im: Image.Image) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / f"{label}.png"
    im.save(p)
    im.crop(CTX_BOX).save(RESULTS / f"{label}_context_crop.png")
    im.crop(GHOST_DETAIL).save(RESULTS / f"{label}_ghost_detail.png")
    return p


def diff_count(a: Image.Image, b: Image.Image, box: tuple[int, int, int, int]) -> int:
    aa = np.asarray(a.crop(box).convert("RGB"))
    bb = np.asarray(b.crop(box).convert("RGB"))
    return int((np.abs(aa.astype(int) - bb.astype(int)).max(axis=2) > 2).sum())


def make_context_board(items: list[tuple[str, Path]]) -> None:
    tile_w, tile_h = 720, 620
    board = Image.new("RGB", (tile_w * 2 + 30, tile_h * 3 + 40), "white")
    d = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items[:6]):
        im = Image.open(path).convert("RGB")
        crop = im.crop(CTX_BOX).resize((680, 520), Image.Resampling.LANCZOS)
        x = 10 + (i % 2) * tile_w
        y = 10 + (i // 2) * tile_h
        d.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 32))
    board.save(RESULTS / "wave11_context_feedback_board.png")


def make_detail_board(items: list[tuple[str, Path]]) -> None:
    tile_w, tile_h = 380, 700
    board = Image.new("RGB", (tile_w * len(items) + 20, tile_h + 50), "white")
    d = ImageDraw.Draw(board)
    for i, (label, path) in enumerate(items):
        im = Image.open(path).convert("RGB")
        crop = im.crop(GHOST_DETAIL).resize((350, 600), Image.Resampling.LANCZOS)
        x = 10 + i * tile_w
        d.text((x, 10), label, fill=(140, 0, 0))
        board.paste(crop, (x, 42))
    board.save(RESULTS / "wave11_ghost_detail_feedback_board.png")


def verify(items: list[tuple[str, Path]]) -> None:
    base = Image.open(BASE).convert("RGB")
    boxes = {
        "context": CTX_BOX,
        "ghost_detail": GHOST_DETAIL,
        "hotel_guard": HOTEL_GUARD,
        "church_guard": CHURCH_GUARD,
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
    (RESULTS / "wave11_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    base = Image.open(BASE).convert("RGB")
    items: list[tuple[str, Path]] = [("baseline hotel fix", BASE)]
    variants = [
        ("v01 whole segment", RAW / "whole_segment_raw.png", INPUTS / "whole_segment_mask.png"),
        ("v02 foliage only", RAW / "foliage_only_raw.png", INPUTS / "foliage_only_mask.png"),
        ("v03 bridge+foliage", RAW / "bridge_wall_foliage_raw.png", INPUTS / "bridge_wall_foliage_mask.png"),
    ]
    for label, raw, mask in variants:
        if raw.exists():
            slug = label.replace(" ", "_")
            items.append((label, save(slug, paste_context(base, raw, mask))))
    items.append(("v04 local control", save("v04_local_control", local_control(base))))
    make_context_board(items)
    make_detail_board(items)
    verify(items)


if __name__ == "__main__":
    main()
