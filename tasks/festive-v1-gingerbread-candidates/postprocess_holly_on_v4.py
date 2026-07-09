#!/usr/bin/env python3
"""Geometry-lock V6/V7 holly fills onto V4 cookie+icing base; write previews + board."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageFont, ImageDraw
from scipy import ndimage

TASK = Path(__file__).resolve().parents[0]
# script lives in task folder when copied; also support running from outputs helper
ROOT = Path(__file__).resolve().parents[2]
if (ROOT / "tasks" / "festive-v1-gingerbread-candidates").exists():
    TASK = ROOT / "tasks" / "festive-v1-gingerbread-candidates"
OUT = TASK / "outputs" / "icing-edge-trails"
MASK_PATH = TASK / "geometry" / "combined-decoration-mask.png"
V4 = OUT / "edge-v4-watercolor-piped-artwork.png"
PROD = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/new cutting files/NEW Festive/Images/candidates"
)
LOCAL = TASK / "Images" / "candidates"
W, H = 1400, 1899
PAPER = (252, 249, 240, 255)

VARIANTS = [
    ("edge-v6-holly-dense", "V6. Dense Holly-Candy on V4", "edge-v6-holly-dense-raw.png"),
    ("edge-v7-holly-sparse", "V7. Sparse Holly-Candy on V4", "edge-v7-holly-sparse-raw.png"),
]


def paper(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3] = PAPER
    arr[:, :, :3] = np.clip(arr[:, :, :3] + rng.normal(0, 3, (H, W, 1)), 0, 255)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(0.2)).convert("RGBA")


def label_font(size: int = 20) -> ImageFont.ImageFont:
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def composite_on_v4(raw_path: Path, mask: np.ndarray, v4: Image.Image) -> Image.Image:
    """Keep V4 icing border; fill interior with generated decorations on cookie."""
    raw = Image.open(raw_path).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
    raw_a = np.array(raw)
    v4_a = np.array(v4.convert("RGBA"))

    # Interior = eroded mask so outer icing from V4 is preserved
    interior = ndimage.binary_erosion(mask, iterations=8)
    # Slightly softer interior edge
    interior_f = ndimage.gaussian_filter(interior.astype(np.float32), 1.2)

    out = v4_a.astype(np.float32).copy()
    # Where interior, blend raw decorations over V4 cookie (favor raw for motifs)
    for c in range(3):
        out[:, :, c] = (1.0 - interior_f) * out[:, :, c] + interior_f * raw_a[:, :, c]
    # Alpha: V4 silhouette (mask + icing halo already in V4)
    # Keep V4 alpha outside interior; inside use max of both
    out[:, :, 3] = np.maximum(v4_a[:, :, 3], interior_f * raw_a[:, :, 3])
    # Hard clear far outside mask+halo
    halo = ndimage.binary_dilation(mask, iterations=10)
    out[~halo, :] = 0
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def metrics(art: Image.Image, mask: np.ndarray) -> dict:
    a = np.array(art)
    alpha = a[:, :, 3] > 20
    allow = ndimage.binary_dilation(mask, iterations=10)
    return {
        "opaque_outside_halo": int((alpha & ~allow).sum()),
        "opaque_inside": int((alpha & mask).sum()),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    PROD.mkdir(parents=True, exist_ok=True)

    mask = np.array(Image.open(MASK_PATH).convert("L").resize((W, H), Image.Resampling.NEAREST)) > 128
    v4 = Image.open(V4).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)

    items = []
    all_m = {}
    for i, (slug, title, raw_name) in enumerate(VARIANTS):
        raw = OUT / raw_name
        if not raw.exists():
            raise SystemExit(f"missing raw: {raw}")
        art = composite_on_v4(raw, mask, v4)
        art_path = OUT / f"{slug}-artwork.png"
        art.save(art_path)
        prev = paper(44000 + i)
        prev.alpha_composite(art)
        prev_path = OUT / f"{slug}-preview.png"
        prev.save(prev_path)
        m = metrics(art, mask)
        all_m[slug] = m
        for src in (art_path, prev_path, raw):
            shutil.copy2(src, PROD / src.name)
            shutil.copy2(src, LOCAL / src.name)
        items.append({"title": title, "slug": slug, "preview": str(prev_path), "metrics": m})
        print(json.dumps({"slug": slug, **m}))

    thumb_w, thumb_h, label_h, gutter = 430, 640, 48, 22
    board = Image.new(
        "RGBA",
        (2 * thumb_w + 3 * gutter, thumb_h + label_h + 2 * gutter),
        (250, 248, 240, 255),
    )
    draw = ImageDraw.Draw(board)
    font = label_font(18)
    for idx, item in enumerate(items):
        img = Image.open(item["preview"]).convert("RGBA")
        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gutter + idx * (thumb_w + gutter)
        y = gutter
        draw.text((x, y), item["title"], fill=(62, 48, 38, 255), font=font)
        board.alpha_composite(img, (x + (thumb_w - img.width) // 2, y + label_h))
    board_path = OUT / "festive-v1-holly-on-v4-board.png"
    board.save(board_path)
    shutil.copy2(board_path, PROD / board_path.name)
    shutil.copy2(board_path, LOCAL / board_path.name)

    ok = all(m["opaque_outside_halo"] == 0 for m in all_m.values())
    report = {"pass": ok, "candidates": items, "board": str(board_path), "metrics": all_m}
    (OUT / "holly-on-v4-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"pass": ok, "board": str(board_path)}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
