#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / "inputs"
RAW = ROOT / "raw"
RESULTS = ROOT / "results"
INPUTS.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)

BASE = Path("tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png")

# Wider inspection crop around the bridge / stair issue.
CROP_BOX = (1720, 2200, 2600, 2940)

# Full-res polygon covering the abruptly-cropped stair continuation area, with
# enough tree/foliage context for the image model to redraw occlusion naturally.
STAIR_POLYGON = [
    (1905, 2360),
    (2445, 2328),
    (2445, 2748),
    (1985, 2770),
    (1858, 2635),
]


def build_mask() -> None:
    base = Image.open(BASE).convert("RGB")
    mask = Image.new("L", base.size, 0)
    d = ImageDraw.Draw(mask)
    d.polygon(STAIR_POLYGON, fill=255)
    hard = mask.filter(ImageFilter.GaussianBlur(2))
    feather = mask.filter(ImageFilter.GaussianBlur(22))
    hard.save(INPUTS / "bridge_stairs_mask_hard.png")
    feather.save(INPUTS / "bridge_stairs_mask_feathered.png")

    overlay = base.copy()
    od = ImageDraw.Draw(overlay, "RGBA")
    od.polygon(STAIR_POLYGON, fill=(120, 220, 40, 90), outline=(40, 180, 20, 255))
    overlay.crop(CROP_BOX).save(INPUTS / "bridge_stairs_mask_overlay_crop.png")
    base.crop(CROP_BOX).save(INPUTS / "bridge_stairs_base_crop.png")


def normalize_raw(raw_path: Path, size: tuple[int, int]) -> Image.Image:
    raw = Image.open(raw_path).convert("RGB")
    if raw.size != size:
        raw = raw.resize(size, Image.Resampling.LANCZOS)
    return raw


def assemble() -> list[tuple[str, Path]]:
    base = Image.open(BASE).convert("RGB")
    mask = Image.open(INPUTS / "bridge_stairs_mask_feathered.png").convert("L")
    outputs: list[tuple[str, Path]] = [("base", BASE)]
    for raw_path in sorted(RAW.glob("*_raw.png")):
        label = raw_path.stem.replace("_raw", "")
        donor = normalize_raw(raw_path, base.size)
        out = Image.composite(donor, base, mask)
        out_path = RESULTS / f"{label}_masked.png"
        out.save(out_path)
        outputs.append((label, out_path))

        diff = ImageChops.difference(base.crop(CROP_BOX), out.crop(CROP_BOX)).convert("L")
        arr = np.asarray(diff)
        heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
        heat[..., 0] = np.clip(arr * 5, 0, 255)
        heat[..., 1] = np.clip(arr * 2, 0, 120)
        Image.blend(base.crop(CROP_BOX), Image.fromarray(heat), 0.48).save(RESULTS / f"{label}_diff_overlay_crop.png")
        out.crop(CROP_BOX).save(RESULTS / f"{label}_crop.png")
    return outputs


def build_board(outputs: list[tuple[str, Path]]) -> None:
    base = Image.open(BASE).convert("RGB")
    tiles = []
    for label, path in outputs:
        im = Image.open(path).convert("RGB") if Path(path).exists() else base
        crop = im.crop(CROP_BOX).resize((704, 592), Image.Resampling.LANCZOS)
        tiles.append((label, crop))
    cols = 2
    tile_w, tile_h = 704, 632
    rows = (len(tiles) + 1) // 2
    board = Image.new("RGB", (cols * tile_w + 30, rows * tile_h + 20), "white")
    d = ImageDraw.Draw(board)
    for i, (label, crop) in enumerate(tiles):
        x = 10 + (i % cols) * (tile_w + 10)
        y = 10 + (i // cols) * tile_h
        d.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 30))
    board.save(RESULTS / "bridge_stairs_openai_donor_board.png")


def verify(outputs: list[tuple[str, Path]]) -> None:
    base = np.asarray(Image.open(BASE).convert("RGB"))
    hard = np.asarray(Image.open(INPUTS / "bridge_stairs_mask_hard.png").convert("L")) > 0
    lines = []
    for label, path in outputs:
        if label == "base":
            continue
        im = np.asarray(Image.open(path).convert("RGB"))
        diff = np.abs(im.astype(int) - base.astype(int)).max(axis=2) > 2
        lines.append(
            f"{label}\tinside_changed={int((diff & hard).sum())}"
            f"\toutside_changed={int((diff & ~hard).sum())}\tpath={Path(path).resolve()}"
        )
    (RESULTS / "bridge_stairs_openai_donor_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    build_mask()
    outputs = assemble()
    build_board(outputs)
    verify(outputs)


if __name__ == "__main__":
    main()
