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

BASE = Path("tasks/berlin-hotel-base/wave6_bridge_stairs_openai_donor/results/stair_architecture_under_foliage_masked.png")

# Full-res context crop around the top-right hotel roof/facade issue.
CROP_BOX = (3350, 950, 3940, 1680)

# The circled issue maps from screenshot x~1772..1882, y~350..520 to roughly
# x~3515..3735, y~1135..1470. The polygon gives the model enough surrounding
# roof/parapet/window context to continue the facade coherently.
EDIT_POLY = [
    (3485, 1080),
    (3765, 1068),
    (3778, 1515),
    (3560, 1542),
    (3452, 1398),
]

# Guard the already-approved bridge-stair region: must remain unchanged.
STAIR_PROTECTED = (1720, 2200, 2600, 2940)


def make_mask(size: tuple[int, int], poly: list[tuple[int, int]], feather: int = 18) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.polygon(poly, fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))


def build_inputs() -> None:
    base = Image.open(BASE).convert("RGB")
    hard = make_mask(base.size, EDIT_POLY, feather=2)
    feather = make_mask(base.size, EDIT_POLY, feather=20)
    hard.save(INPUTS / "hotel_roof_facade_mask_hard.png")
    feather.save(INPUTS / "hotel_roof_facade_mask_feathered.png")
    base.crop(CROP_BOX).save(INPUTS / "hotel_roof_facade_base_crop.png")
    overlay = base.copy()
    d = ImageDraw.Draw(overlay, "RGBA")
    d.polygon(EDIT_POLY, fill=(120, 220, 40, 90), outline=(40, 180, 20, 255))
    overlay.crop(CROP_BOX).save(INPUTS / "hotel_roof_facade_mask_overlay_crop.png")


def normalize(raw: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(raw).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.Resampling.LANCZOS)
    return im


def assemble() -> list[tuple[str, Path]]:
    base = Image.open(BASE).convert("RGB")
    mask = Image.open(INPUTS / "hotel_roof_facade_mask_feathered.png").convert("L")
    outputs: list[tuple[str, Path]] = [("base", BASE)]
    for raw_path in sorted(RAW.glob("*_raw.png")):
        label = raw_path.stem.replace("_raw", "")
        out = Image.composite(normalize(raw_path, base.size), base, mask)
        out_path = RESULTS / f"{label}_masked.png"
        out.save(out_path)
        out.crop(CROP_BOX).save(RESULTS / f"{label}_crop.png")

        diff = ImageChops.difference(base.crop(CROP_BOX), out.crop(CROP_BOX)).convert("L")
        arr = np.asarray(diff)
        heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
        heat[..., 0] = np.clip(arr * 5, 0, 255)
        heat[..., 1] = np.clip(arr * 2, 0, 120)
        Image.blend(base.crop(CROP_BOX), Image.fromarray(heat), 0.48).save(
            RESULTS / f"{label}_diff_overlay_crop.png"
        )
        outputs.append((label, out_path))
    return outputs


def board(outputs: list[tuple[str, Path]]) -> None:
    base = Image.open(BASE).convert("RGB")
    tile_w, tile_h = 590, 730
    cols = 2
    rows = (len(outputs) + 1) // 2
    out = Image.new("RGB", (cols * tile_w + 30, rows * tile_h + 20), "white")
    d = ImageDraw.Draw(out)
    for i, (label, path) in enumerate(outputs):
        im = Image.open(path).convert("RGB") if path.exists() else base
        crop = im.crop(CROP_BOX).resize((560, 694), Image.Resampling.LANCZOS)
        x = 10 + (i % cols) * tile_w
        y = 10 + (i // 2) * tile_h
        d.text((x, y), label, fill=(140, 0, 0))
        out.paste(crop, (x, y + 30))
    out.save(RESULTS / "hotel_roof_facade_openai_donor_board.png")


def verify(outputs: list[tuple[str, Path]]) -> None:
    base = np.asarray(Image.open(BASE).convert("RGB"))
    hard = np.asarray(Image.open(INPUTS / "hotel_roof_facade_mask_hard.png").convert("L")) > 0
    sx0, sy0, sx1, sy1 = STAIR_PROTECTED
    stair = np.zeros(base.shape[:2], dtype=bool)
    stair[sy0:sy1, sx0:sx1] = True
    lines = []
    for label, path in outputs:
        if label == "base":
            continue
        im = np.asarray(Image.open(path).convert("RGB"))
        diff = np.abs(im.astype(int) - base.astype(int)).max(axis=2) > 2
        lines.append(
            f"{label}\tinside_changed={int((diff & hard).sum())}"
            f"\toutside_changed={int((diff & ~hard).sum())}"
            f"\tstair_protected_changed={int((diff & stair).sum())}"
            f"\tpath={Path(path).resolve()}"
        )
    (RESULTS / "hotel_roof_facade_openai_donor_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    build_inputs()
    outputs = assemble()
    board(outputs)
    verify(outputs)


if __name__ == "__main__":
    main()
