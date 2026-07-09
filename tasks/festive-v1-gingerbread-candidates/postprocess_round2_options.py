#!/usr/bin/env python3
"""Exact-mask postprocess for round2 styled options + comparison board."""
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "festive-v1-gingerbread-candidates"
MASK = TASK / "geometry" / "combined-decoration-mask.png"
OUT = TASK / "outputs" / "round2-options"
PROD = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/new cutting files/NEW Festive/Images/candidates"
)
W, H = 1400, 1899
PAPER = (252, 249, 240, 255)

VARIANTS = [
    ("opt-a-royal-icing-cookie-trim", "A. Royal Icing Cookie Trim"),
    ("opt-b-candy-cane-holly-cascade", "B. Candy Cane Holly Cascade"),
    ("opt-c-frosted-snowflake-lattice", "C. Frosted Snowflake Lattice"),
]


def paper(size: tuple[int, int], seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3] = PAPER
    arr[:, :, :3] = np.clip(arr[:, :, :3] + rng.normal(0, 3, (size[1], size[0], 1)), 0, 255)
    return Image.fromarray(arr, "RGBA").filter(ImageFilter.GaussianBlur(0.2))


def label_font(size: int = 26) -> ImageFont.ImageFont:
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def outline_from_mask(mask: Image.Image) -> Image.Image:
    edge = mask.filter(ImageFilter.FIND_EDGES)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_alpha = edge.point(lambda v: 120 if v > 12 else 0)
    stroke = Image.new("RGBA", (W, H), (92, 74, 52, 0))
    stroke.putalpha(draw_alpha)
    out.alpha_composite(stroke)
    return out


def count_outside(path: Path, mask: Image.Image) -> int:
    img = Image.open(path).convert("RGBA")
    alpha = img.getchannel("A")
    outside = ImageChops.subtract(alpha, mask)
    return sum(1 for v in outside.getdata() if v > 0)


def make_board(items: list[dict]) -> Path:
    thumb_w, thumb_h, label_h, gutter = 430, 640, 50, 22
    cols = 3
    rows = math.ceil(len(items) / cols)
    board = Image.new(
        "RGBA",
        (cols * thumb_w + (cols + 1) * gutter, rows * (thumb_h + label_h) + (rows + 1) * gutter),
        (250, 248, 240, 255),
    )
    draw = ImageDraw.Draw(board, "RGBA")
    font = label_font(22)
    for idx, item in enumerate(items):
        img = Image.open(item["preview"]).convert("RGBA")
        img.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gutter + (idx % cols) * (thumb_w + gutter)
        y = gutter + (idx // cols) * (thumb_h + label_h + gutter)
        draw.text((x, y), item["title"], fill=(62, 48, 38, 255), font=font)
        board.alpha_composite(img, (x + (thumb_w - img.width) // 2, y + label_h))
    path = OUT / "festive-v1-round2-options-board.png"
    board.save(path)
    PROD.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, PROD / path.name)
    return path


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PROD.mkdir(parents=True, exist_ok=True)
    mask = Image.open(MASK).convert("L").resize((W, H), Image.Resampling.LANCZOS)
    outline = outline_from_mask(mask)
    manifest = []
    outside = {}
    for idx, (slug, title) in enumerate(VARIANTS, start=1):
        raw = OUT / f"{slug}-raw.png"
        if not raw.exists():
            raise SystemExit(f"missing raw: {raw}")
        fitted = Image.open(raw).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
        art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        art.alpha_composite(fitted)
        art.putalpha(mask)
        art_path = OUT / f"{slug}-artwork.png"
        art.save(art_path)

        preview = paper((W, H), 31000 + idx)
        preview.alpha_composite(art)
        preview.alpha_composite(outline)
        preview_path = OUT / f"{slug}-preview.png"
        preview.save(preview_path)

        for src in (raw, art_path, preview_path):
            shutil.copy2(src, PROD / src.name)

        outside[art_path.name] = count_outside(art_path, mask)
        manifest.append(
            {
                "title": title,
                "slug": slug,
                "raw": str(raw),
                "artwork": str(art_path),
                "preview": str(preview_path),
                "production_preview": str(PROD / preview_path.name),
                "outside_alpha_pixels": outside[art_path.name],
                "method": "openai-subgen-reference-attached",
            }
        )

    board = make_board(manifest)
    report = {
        "candidates": manifest,
        "board": str(board),
        "production_board": str(PROD / board.name),
        "outside_alpha_pixels": outside,
        "pass": all(v == 0 for v in outside.values()) and len(manifest) == 3,
    }
    report_path = OUT / "round2-verification-report.json"
    report_path.write_text(json.dumps(report, indent=2))
    (OUT / "round2-manifest.json").write_text(json.dumps({"candidates": manifest, "board": str(board)}, indent=2))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
