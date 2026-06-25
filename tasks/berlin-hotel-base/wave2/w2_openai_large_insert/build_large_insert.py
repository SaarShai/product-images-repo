#!/usr/bin/env python3
"""Exploratory larger masked insertion of the liked OpenAI tower plates."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


ROOT = Path("tasks/berlin-hotel-base")
OUTDIR = ROOT / "wave2/w2_openai_large_insert"
SRC = ROOT / "work/src.png"
PLATES = [
    ROOT / "work/building_recreate/cand_openai_p1.png",
    ROOT / "work/building_recreate/cand_openai_p2.png",
    ROOT / "work/building_recreate/cand_openai_p3.png",
]
LARGE_BOX = (3000, 780, 4120, 2860)
ZOOM = (2850, 760, 4192, 2900)


def plate_mask(im: Image.Image) -> tuple[Image.Image, Image.Image]:
    arr = np.asarray(im.convert("RGB"))
    # The generated plates are on off-white paper; keep building ink/wash.
    luma = arr.mean(axis=2)
    chroma = arr.std(axis=2)
    mask = ((luma < 238) | (chroma > 8)).astype(np.uint8) * 255
    mask = Image.fromarray(mask, "L").filter(ImageFilter.GaussianBlur(1.0))
    bbox = mask.point(lambda v: 255 if v > 25 else 0).getbbox()
    if not bbox:
        raise RuntimeError("empty donor mask")
    return im.crop(bbox).convert("RGB"), mask.crop(bbox)


def color_harmonize(im: Image.Image, target: Image.Image) -> Image.Image:
    arr = np.asarray(im.convert("RGB")).astype(np.float32)
    tar = np.asarray(target.convert("RGB")).astype(np.float32)
    am, ast = arr.reshape(-1, 3).mean(0), arr.reshape(-1, 3).std(0)
    tm, ts = tar.reshape(-1, 3).mean(0), tar.reshape(-1, 3).std(0)
    arr = (arr - am) / np.maximum(ast, 1) * np.maximum(ts * 0.9, 1) + tm
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    out = ImageEnhance.Color(out).enhance(0.76)
    out = ImageEnhance.Contrast(out).enhance(0.9)
    return out


def place_plate(plate_path: Path, name: str, target_box: tuple[int, int, int, int], x_shift: int = 0, y_shift: int = 0, scale: float = 1.0) -> Path:
    src = Image.open(SRC).convert("RGB")
    donor, mask = plate_mask(Image.open(plate_path).convert("RGB"))
    target_w = target_box[2] - target_box[0]
    target_h = target_box[3] - target_box[1]
    donor_aspect = donor.width / donor.height
    h = int(target_h * scale)
    w = int(h * donor_aspect)
    donor = donor.resize((w, h), Image.Resampling.LANCZOS)
    mask = mask.resize((w, h), Image.Resampling.LANCZOS)
    donor = color_harmonize(donor, src.crop(target_box))

    canvas = Image.new("RGB", src.size, (255, 255, 255))
    alpha = Image.new("L", src.size, 0)
    x = target_box[0] + (target_w - w) // 2 + x_shift
    y = target_box[1] + (target_h - h) // 2 + y_shift
    canvas.paste(donor, (x, y))
    alpha.paste(mask, (x, y))

    # Preserve non-hotel foreground edges at the bottom/left a bit.
    draw = ImageDraw.Draw(alpha)
    draw.rectangle((0, target_box[3] - 55, src.width, src.height), fill=0)
    alpha = alpha.filter(ImageFilter.GaussianBlur(2.2))
    box_clip = Image.new("L", src.size, 0)
    ImageDraw.Draw(box_clip).rectangle(target_box, fill=255)
    alpha = ImageChops.multiply(alpha, box_clip)
    out = Image.composite(canvas, src, alpha)
    out_path = OUTDIR / f"{name}.png"
    out.save(out_path)
    out.crop(ZOOM).save(OUTDIR / f"{name}_zoom.png")
    return out_path


def make_contact(paths: list[Path]) -> None:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 24)
    tiles = []
    for p in paths:
        im = Image.open(OUTDIR / f"{p.stem}_zoom.png").convert("RGB")
        im = im.resize((760, int(im.height * 760 / im.width)), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (760, im.height + 44), "white")
        d = ImageDraw.Draw(tile)
        d.text((8, 8), p.name, fill=(160, 0, 0), font=font)
        tile.paste(im, (0, 44))
        tiles.append(tile)
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    out = Image.new("RGB", (cols * 760, rows * max(t.height for t in tiles)), "white")
    for i, t in enumerate(tiles):
        out.paste(t, ((i % cols) * 760, (i // cols) * t.height))
    out.save(OUTDIR / "large_insert_contact.png")


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    outputs = []
    outputs.append(place_plate(PLATES[0], "large_openai_p1_full_mask_fit", LARGE_BOX, x_shift=8, y_shift=20, scale=1.01))
    outputs.append(place_plate(PLATES[1], "large_openai_p2_full_mask_fit", LARGE_BOX, x_shift=8, y_shift=20, scale=1.01))
    outputs.append(place_plate(PLATES[2], "large_openai_p3_full_mask_fit", LARGE_BOX, x_shift=8, y_shift=20, scale=1.01))
    outputs.append(place_plate(PLATES[0], "large_openai_p1_lower_shifted", LARGE_BOX, x_shift=22, y_shift=78, scale=0.93))
    make_contact(outputs)
    (OUTDIR / "method_notes.md").write_text(
        "# w2_openai_large_insert\n\n"
        "Exploratory large-mask insertion after user feedback that OpenAI standalone plates look good and insertion is the hard part. "
        f"These intentionally use a larger edit box `{','.join(map(str, LARGE_BOX))}` and are not base-only safe candidates. "
        "They test whether the full generated tower can breathe as an integrated source rather than being squeezed into the base band.\n",
        encoding="utf-8",
    )
    print(f"wrote {len(outputs)} large insertion candidates to {OUTDIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
