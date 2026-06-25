#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)

BASE = Path("tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png")

# Full-resolution crop around the bridge/stairs area.
CROP_BOX = (1880, 2450, 2320, 2780)

# Coordinates inside the crop.
SOURCE_STAIR = (70, 88, 210, 210)
TARGET = (205, 92, 355, 210)


def feather_rect(size: tuple[int, int], box: tuple[int, int, int, int], feather: int = 14) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.rectangle(box, fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))


def foliage_mask(crop: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    """Approximate foreground trees/branches so they stay on top of the stair continuation."""
    arr = np.array(crop.convert("RGB"))
    x0, y0, x1, y1 = box
    sub = arr[y0:y1, x0:x1].astype(np.int16)
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    # Foliage/branches here are green-yellow/darker than the pale stone stair wash.
    greenish = (g >= r - 10) & (g >= b - 4) & (g < 225)
    darker = ((r + g + b) / 3 < 168)
    edges = cv2.Canny(sub.astype(np.uint8), 35, 95) > 0
    m = ((greenish & darker) | edges).astype(np.uint8) * 255
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)), iterations=1)
    m = cv2.GaussianBlur(m, (0, 0), 1.4)
    full = np.zeros(arr.shape[:2], dtype=np.uint8)
    full[y0:y1, x0:x1] = m
    return Image.fromarray(full, "L")


def make_donor(crop: Image.Image, opacity: float, sharpen: float = 1.0) -> Image.Image:
    src = crop.crop(SOURCE_STAIR)
    # Avoid copying the strong vertical pole from the far-left source.
    src = src.crop((18, 0, src.width, src.height))
    target_w = TARGET[2] - TARGET[0]
    target_h = TARGET[3] - TARGET[1]
    donor = src.resize((target_w, target_h), Image.Resampling.BICUBIC)
    donor = ImageEnhance.Contrast(donor).enhance(0.86)
    donor = ImageEnhance.Color(donor).enhance(0.72)
    if sharpen != 1.0:
        donor = ImageEnhance.Sharpness(donor).enhance(sharpen)

    # Fade the continuation as it moves right, because it should sit behind trees.
    alpha = Image.new("L", (target_w, target_h), 0)
    aa = np.zeros((target_h, target_w), dtype=np.float32)
    for x in range(target_w):
        aa[:, x] = opacity * (0.95 - 0.34 * (x / max(1, target_w - 1)))
    alpha = Image.fromarray(np.clip(aa * 255, 0, 255).astype(np.uint8), "L")

    layer = Image.new("RGB", crop.size, (0, 0, 0))
    layer.paste(donor, TARGET[:2])
    mask = Image.new("L", crop.size, 0)
    mask.paste(alpha, TARGET[:2])
    mask = Image.composite(mask, Image.new("L", crop.size, 0), feather_rect(crop.size, TARGET, 10))

    out = Image.composite(layer, crop, mask)
    # Put the original foliage/branch detail back over the stairs.
    tree = foliage_mask(crop, TARGET)
    out = Image.composite(crop, out, tree)
    return out


def linework_assist(crop: Image.Image) -> Image.Image:
    out = crop.copy()
    d = ImageDraw.Draw(out, "RGBA")
    x0, y0, x1, y1 = TARGET
    # Continue the visible tread rhythm without filling the whole region.
    for y in [105, 113, 121, 130, 139, 149, 159, 170, 182, 195]:
        d.line((x0 + 2, y, x1 - 6, y + 1), fill=(108, 98, 82, 54), width=2)
        d.line((x0 + 2, y + 3, x1 - 7, y + 4), fill=(235, 226, 202, 36), width=2)
    tree = foliage_mask(crop, TARGET)
    return Image.composite(crop, out, ImageChops_invert_soft(tree, feather_rect(crop.size, TARGET, 8)))


def ImageChops_invert_soft(tree: Image.Image, region: Image.Image) -> Image.Image:
    arr = np.array(region).astype(np.int16) - (np.array(tree).astype(np.int16) * 0.9)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L")


def paste_crop(base: Image.Image, repaired_crop: Image.Image, out_path: Path, label: str) -> None:
    crop_mask = Image.new("L", base.size, 0)
    local = feather_rect((CROP_BOX[2] - CROP_BOX[0], CROP_BOX[3] - CROP_BOX[1]), TARGET, 10)
    crop_mask.paste(local, CROP_BOX[:2])
    layer = base.copy()
    layer.paste(repaired_crop, CROP_BOX[:2])
    Image.composite(layer, base, crop_mask).save(out_path)

    debug = repaired_crop.copy()
    d = ImageDraw.Draw(debug, "RGBA")
    d.rectangle(TARGET, outline=(80, 210, 40, 255), width=4)
    d.text((8, 8), label, fill=(140, 0, 0, 255))
    debug.save(OUT / f"{out_path.stem}_crop.png")


def build_board(paths: list[tuple[str, Path]]) -> None:
    base = Image.open(BASE).convert("RGB")
    crops = []
    for label, p in paths:
        im = Image.open(p).convert("RGB") if p.exists() else base
        crop = im.crop(CROP_BOX).resize((660, 495), Image.Resampling.LANCZOS)
        crops.append((label, crop))
    w, h = 660, 535
    board = Image.new("RGB", (2 * w + 30, ((len(crops) + 1) // 2) * h + 20), "white")
    d = ImageDraw.Draw(board)
    for i, (label, crop) in enumerate(crops):
        x = 10 + (i % 2) * (w + 10)
        y = 10 + (i // 2) * h
        d.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 32))
    board.save(OUT / "bridge_stairs_repair_board.png")


def verify(paths: list[tuple[str, Path]]) -> None:
    base = np.array(Image.open(BASE).convert("RGB"))
    allowed = np.zeros(base.shape[:2], dtype=bool)
    x0, y0, _, _ = CROP_BOX
    tx0, ty0, tx1, ty1 = TARGET
    allowed[y0 + ty0 - 18:y0 + ty1 + 18, x0 + tx0 - 18:x0 + tx1 + 18] = True
    lines = []
    for label, p in paths:
        if label == "base":
            continue
        im = np.array(Image.open(p).convert("RGB"))
        diff = np.abs(im.astype(int) - base.astype(int)).max(axis=2) > 2
        lines.append(f"{label}\tinside_changed={int((diff & allowed).sum())}\toutside_changed={int((diff & ~allowed).sum())}\tpath={p.resolve()}")
    (OUT / "bridge_stairs_repair_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    base = Image.open(BASE).convert("RGB")
    crop = base.crop(CROP_BOX)
    crop.save(OUT / "bridge_stairs_base_crop.png")

    variants = [("base", BASE)]
    configs = [
        ("v01_stair_continuation_subtle", 0.48, 0.95),
        ("v02_stair_continuation_medium", 0.66, 1.00),
        ("v03_stair_continuation_stronger", 0.82, 1.08),
    ]
    for stem, opacity, sharp in configs:
        repaired = make_donor(crop, opacity=opacity, sharpen=sharp)
        out_path = OUT / f"{stem}.png"
        paste_crop(base, repaired, out_path, stem)
        variants.append((stem, out_path))

    # Linework-only backup for comparison.
    line = linework_assist(crop)
    out_path = OUT / "v04_linework_tread_hint_only.png"
    paste_crop(base, line, out_path, "v04_linework_tread_hint_only")
    variants.append(("v04_linework_tread_hint_only", out_path))

    build_board(variants)
    verify(variants)


if __name__ == "__main__":
    main()
