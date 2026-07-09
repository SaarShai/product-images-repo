#!/usr/bin/env python3
"""Composite V8/V9 onto V6: keep V6 elsewhere; take chimney+tree from gen; high-res previews."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "festive-v1-gingerbread-candidates"
OUT = TASK / "outputs" / "icing-edge-trails"
PROD = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/festive/images"
)
CAND = PROD / "candidates"
LOCAL = TASK / "Images" / "candidates"
MASK_ALL = OUT / "mask-all-with-tree.png"
MASK_CHIMNEY = OUT / "mask-chimney.png"
MASK_TREE = OUT / "mask-tree.png"
V6 = PROD / "edge-v6-holly-dense-artwork.png"
W, H = 1400, 1899
PAPER = (252, 249, 240, 255)

VARIANTS = [
    ("edge-v8-brick-tree", "V8. Brick Chimney + Gingerbread Tree", "edge-v8-brick-tree-raw.png"),
    ("edge-v9-softbrick-tree", "V9. Soft Brick + Ornament Tree", "edge-v9-softbrick-tree-raw.png"),
]


def paper(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.zeros((H, W, 4), dtype=np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3] = PAPER
    arr[:, :, :3] = np.clip(arr[:, :, :3] + rng.normal(0, 3, (H, W, 1)), 0, 255)
    return Image.fromarray(arr).filter(ImageFilter.GaussianBlur(0.2)).convert("RGBA")


def label_font(size: int = 18) -> ImageFont.ImageFont:
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def soft_mask(m: np.ndarray, erode: int = 0, blur: float = 1.0) -> np.ndarray:
    x = m.copy()
    if erode > 0:
        x = ndimage.binary_erosion(x, iterations=erode)
    return ndimage.gaussian_filter(x.astype(np.float32), blur)


def composite(raw_path: Path, v6: np.ndarray, chimney: np.ndarray, tree: np.ndarray, all_mask: np.ndarray) -> Image.Image:
    raw = np.array(Image.open(raw_path).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)).astype(np.float32)
    out = v6.astype(np.float32).copy()

    # Replace chimney + tree regions from generation (include slight halo for icing border)
    for region in (chimney, tree):
        zone = ndimage.binary_dilation(region, iterations=6)
        w = soft_mask(zone, erode=0, blur=1.2)
        for c in range(4):
            out[:, :, c] = (1.0 - w) * out[:, :, c] + w * raw[:, :, c]

    # Ensure tree exists even if gen weak: keep gen where tree mask
    tw = soft_mask(tree, erode=0, blur=0.8)
    for c in range(4):
        out[:, :, c] = (1.0 - tw) * out[:, :, c] + tw * raw[:, :, c]

    # Clear far outside combined mask+halo
    allow = ndimage.binary_dilation(all_mask, iterations=10)
    out[~allow] = 0
    # Force alpha inside all cutouts at least from max(v6, raw)
    inside = all_mask
    out[inside, 3] = np.maximum(out[inside, 3], 255)

    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    LOCAL.mkdir(parents=True, exist_ok=True)
    CAND.mkdir(parents=True, exist_ok=True)
    PROD.mkdir(parents=True, exist_ok=True)

    all_mask = np.array(Image.open(MASK_ALL).convert("L").resize((W, H), Image.Resampling.NEAREST)) > 128
    chimney = np.array(Image.open(MASK_CHIMNEY).convert("L").resize((W, H), Image.Resampling.NEAREST)) > 128
    tree = np.array(Image.open(MASK_TREE).convert("L").resize((W, H), Image.Resampling.NEAREST)) > 128
    v6 = np.array(Image.open(V6).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS))

    items = []
    metrics = {}
    for i, (slug, title, raw_name) in enumerate(VARIANTS):
        raw = OUT / raw_name
        if not raw.exists():
            raise SystemExit(f"missing {raw}")
        art = composite(raw, v6, chimney, tree, all_mask)
        art_path = OUT / f"{slug}-artwork.png"
        art.save(art_path)
        # also save high-res lossless-ish PNG already 1400x1899; upsample 2x for "high-res" review
        hi = art.resize((W * 2, H * 2), Image.Resampling.LANCZOS)
        hi_path = OUT / f"{slug}-artwork-2x.png"
        hi.save(hi_path, optimize=True)

        prev = paper(45000 + i)
        prev.alpha_composite(art)
        prev_path = OUT / f"{slug}-preview.png"
        prev.save(prev_path)
        prev2 = paper(45100 + i).resize((W * 2, H * 2), Image.Resampling.LANCZOS)
        prev2.alpha_composite(hi)
        prev2_path = OUT / f"{slug}-preview-2x.png"
        prev2.save(prev2_path, optimize=True)

        a = np.array(art)
        allow = ndimage.binary_dilation(all_mask, iterations=10)
        m = {
            "opaque_outside": int(((a[:, :, 3] > 20) & ~allow).sum()),
            "tree_coverage": int(((a[:, :, 3] > 20) & tree).sum()),
            "chimney_coverage": int(((a[:, :, 3] > 20) & chimney).sum()),
        }
        metrics[slug] = m
        for src in (art_path, hi_path, prev_path, prev2_path, raw):
            shutil.copy2(src, CAND / src.name)
            shutil.copy2(src, LOCAL / src.name)
            shutil.copy2(src, PROD / src.name)
        items.append({"title": title, "slug": slug, "preview": str(prev_path), "preview_2x": str(prev2_path), "artwork": str(art_path), "artwork_2x": str(hi_path), "metrics": m})
        print(json.dumps({"slug": slug, **m}))

    thumb_w, thumb_h, label_h, gutter = 430, 640, 50, 22
    board = Image.new("RGBA", (2 * thumb_w + 3 * gutter, thumb_h + label_h + 2 * gutter), (250, 248, 240, 255))
    draw = ImageDraw.Draw(board)
    font = label_font(17)
    for idx, item in enumerate(items):
        img = Image.open(item["preview"]).convert("RGBA")
        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gutter + idx * (thumb_w + gutter)
        y = gutter
        draw.text((x, y), item["title"], fill=(62, 48, 38, 255), font=font)
        board.alpha_composite(img, (x + (thumb_w - img.width) // 2, y + label_h))
    board_path = OUT / "festive-v1-brick-tree-board.png"
    board.save(board_path)
    for dest in (CAND, LOCAL, PROD):
        shutil.copy2(board_path, dest / board_path.name)

    ok = all(m["opaque_outside"] == 0 and m["tree_coverage"] > 1000 and m["chimney_coverage"] > 1000 for m in metrics.values())
    report = {"pass": ok, "candidates": items, "board": str(board_path), "metrics": metrics}
    (OUT / "brick-tree-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({"pass": ok, "board": str(board_path)}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
