#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results_v2"
OUT.mkdir(parents=True, exist_ok=True)

BASE = Path("tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png")

# Wider crop centered on the Berliner Dom stairs above the bridge.
CROP_BOX = (1720, 2200, 2600, 2940)
CROP_W = CROP_BOX[2] - CROP_BOX[0]
CROP_H = CROP_BOX[3] - CROP_BOX[1]

# Crop-local stair source and target continuation zone.
SOURCE_STAIR = (75, 250, 360, 548)
TARGET_STAIR = (315, 258, 690, 555)


def soft_mask(size: tuple[int, int], box: tuple[int, int, int, int], feather: int, opacity: float = 1.0) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    # Slight trapezoid: stairs should read as receding behind the trees, not a rectangular patch.
    x0, y0, x1, y1 = box
    poly = [(x0, y0 + 18), (x1, y0), (x1 - 8, y1), (x0 - 10, y1 - 2)]
    d.polygon(poly, fill=round(255 * opacity))
    return m.filter(ImageFilter.GaussianBlur(feather))


def foliage_weight(crop: Image.Image, box: tuple[int, int, int, int]) -> Image.Image:
    arr = np.array(crop.convert("RGB"))
    x0, y0, x1, y1 = box
    sub = arr[y0:y1, x0:x1].astype(np.int16)
    r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
    green = (g > r - 12) & (g > b - 8) & (g < 220)
    dark = ((r + g + b) / 3 < 175)
    edge = cv2.Canny(sub.astype(np.uint8), 30, 90) > 0
    m = ((green & dark) | edge).astype(np.uint8) * 255
    m = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)), iterations=1)
    m = cv2.GaussianBlur(m, (0, 0), 1.4)
    full = np.zeros(arr.shape[:2], dtype=np.uint8)
    full[y0:y1, x0:x1] = m
    return Image.fromarray(full)


def make_stair_donor(crop: Image.Image, contrast: float = 0.9, color: float = 0.78) -> Image.Image:
    src = crop.crop(SOURCE_STAIR)
    donor = src.resize((TARGET_STAIR[2] - TARGET_STAIR[0], TARGET_STAIR[3] - TARGET_STAIR[1]), Image.Resampling.BICUBIC)
    donor = ImageEnhance.Contrast(donor).enhance(contrast)
    donor = ImageEnhance.Color(donor).enhance(color)

    layer = crop.copy()
    layer.paste(donor, TARGET_STAIR[:2])
    return layer


def add_tread_lines(crop: Image.Image, strength: int = 58) -> Image.Image:
    out = crop.copy()
    d = ImageDraw.Draw(out, "RGBA")
    x0, y0, x1, y1 = TARGET_STAIR
    # Continue the visible tread rhythm from the left stairs. These lines are intentionally
    # visible, then partially hidden by foliage after compositing.
    ys = [287, 300, 313, 326, 340, 354, 369, 385, 401, 418, 436, 455, 475, 496, 518, 540]
    for idx, y in enumerate(ys):
        tilt = int((y - y0) * 0.035)
        d.line((x0 - 10, y + tilt, x1 + 8, y + tilt - 2), fill=(91, 83, 71, strength), width=3)
        d.line((x0 - 6, y + tilt + 4, x1 + 3, y + tilt + 2), fill=(238, 230, 204, max(24, strength - 18)), width=2)
    return out


def variant(base_crop: Image.Image, donor_alpha: float, line_strength: int, tree_restore: float, name: str) -> Image.Image:
    donor_layer = make_stair_donor(base_crop)
    line_layer = add_tread_lines(donor_layer, line_strength)
    m = soft_mask(base_crop.size, TARGET_STAIR, feather=18, opacity=donor_alpha)
    repaired = Image.composite(line_layer, base_crop, m)

    # Put some original tree/branch structure back in front, but not 100%; otherwise the
    # stair continuation disappears exactly as in v1.
    trees = foliage_weight(base_crop, TARGET_STAIR)
    trees = ImageEnhance.Brightness(trees).enhance(tree_restore)
    repaired = Image.composite(base_crop, repaired, trees)

    marked = repaired.copy()
    d = ImageDraw.Draw(marked, "RGBA")
    d.polygon(
        [
            (TARGET_STAIR[0], TARGET_STAIR[1] + 18),
            (TARGET_STAIR[2], TARGET_STAIR[1]),
            (TARGET_STAIR[2] - 8, TARGET_STAIR[3]),
            (TARGET_STAIR[0] - 10, TARGET_STAIR[3] - 2),
        ],
        outline=(80, 210, 40, 255),
        width=5,
    )
    marked.save(OUT / f"{name}_marked_crop.png")
    return repaired


def paste_to_full(base: Image.Image, crop: Image.Image, name: str) -> Path:
    full_layer = base.copy()
    full_layer.paste(crop, CROP_BOX[:2])
    crop_mask = Image.new("L", base.size, 0)
    local = soft_mask((CROP_W, CROP_H), TARGET_STAIR, feather=22, opacity=1.0)
    crop_mask.paste(local, CROP_BOX[:2])
    out = Image.composite(full_layer, base, crop_mask)
    path = OUT / f"{name}.png"
    out.save(path)
    return path


def diff_crop(base_crop: Image.Image, repaired_crop: Image.Image, name: str) -> None:
    diff = ImageChops.difference(base_crop, repaired_crop).convert("L")
    arr = np.array(diff)
    heat = np.zeros((arr.shape[0], arr.shape[1], 3), dtype=np.uint8)
    heat[..., 0] = np.clip(arr * 5, 0, 255)
    heat[..., 1] = np.clip(arr * 2, 0, 140)
    overlay = Image.blend(base_crop.convert("RGB"), Image.fromarray(heat), 0.48)
    overlay.save(OUT / f"{name}_diff_overlay_crop.png")


def build_board(items: list[tuple[str, Path]]) -> None:
    base = Image.open(BASE).convert("RGB")
    labels_crops = []
    for label, path in items:
        im = Image.open(path).convert("RGB") if path.exists() else base
        crop = im.crop(CROP_BOX).resize((704, 592), Image.Resampling.LANCZOS)
        labels_crops.append((label, crop))
    cols = 2
    tile_w, tile_h = 704, 632
    rows = (len(labels_crops) + 1) // 2
    board = Image.new("RGB", (cols * tile_w + 30, rows * tile_h + 20), "white")
    d = ImageDraw.Draw(board)
    for i, (label, crop) in enumerate(labels_crops):
        x = 10 + (i % cols) * (tile_w + 10)
        y = 10 + (i // cols) * tile_h
        d.text((x, y), label, fill=(140, 0, 0))
        board.paste(crop, (x, y + 30))
    board.save(OUT / "bridge_stairs_v2_board.png")


def verify(items: list[tuple[str, Path]]) -> None:
    base = np.array(Image.open(BASE).convert("RGB"))
    allowed = np.zeros(base.shape[:2], dtype=bool)
    x0, y0 = CROP_BOX[:2]
    tx0, ty0, tx1, ty1 = TARGET_STAIR
    allowed[y0 + ty0 - 35:y0 + ty1 + 35, x0 + tx0 - 35:x0 + tx1 + 35] = True
    lines = []
    for label, path in items:
        if label == "base":
            continue
        im = np.array(Image.open(path).convert("RGB"))
        diff = np.abs(im.astype(int) - base.astype(int)).max(axis=2) > 2
        lines.append(f"{label}\tinside_changed={int((diff & allowed).sum())}\toutside_changed={int((diff & ~allowed).sum())}\tpath={path.resolve()}")
    (OUT / "bridge_stairs_v2_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    base = Image.open(BASE).convert("RGB")
    base_crop = base.crop(CROP_BOX)
    base_crop.save(OUT / "base_wide_crop.png")

    configs = [
        ("v05_visible_stair_continuation", 0.58, 50, 0.62),
        ("v06_stronger_stair_continuation", 0.74, 70, 0.48),
        ("v07_max_readable_stair_continuation", 0.92, 88, 0.34),
    ]
    items: list[tuple[str, Path]] = [("base", BASE)]
    for name, donor_alpha, line_strength, tree_restore in configs:
        repaired_crop = variant(base_crop, donor_alpha, line_strength, tree_restore, name)
        diff_crop(base_crop, repaired_crop, name)
        path = paste_to_full(base, repaired_crop, name)
        items.append((name, path))

    build_board(items)
    verify(items)


if __name__ == "__main__":
    main()
