#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "festive-v1-gingerbread-candidates"
OUT = TASK / "outputs" / "ab5-styled-generated"
MASK = TASK / "outputs" / "ab5-cutout-options" / "ab5-combined-mask.png"
PROD = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/festive/images/Images/candidates"
)
W, H = 1600, 1936
PAPER = (252, 249, 240, 255)

VARIANTS = [
    ("ab5-styled-v1-peppermint-holly", "Styled AB5 V1 - Peppermint Holly Icing"),
    ("ab5-styled-v2-gumdrop-icing", "Styled AB5 V2 - Gumdrop Royal Icing"),
]


def paper(size: tuple[int, int], seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
    arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3] = PAPER
    arr[:, :, :3] = np.clip(arr[:, :, :3] + rng.normal(0, 3, (size[1], size[0], 1)), 0, 255)
    return Image.fromarray(arr, "RGBA").filter(ImageFilter.GaussianBlur(0.2))


def label_font(size: int = 24) -> ImageFont.ImageFont:
    for path in ["/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def outline_from_mask(mask: Image.Image) -> Image.Image:
    edge = mask.filter(ImageFilter.FIND_EDGES)
    alpha = edge.point(lambda v: 125 if v > 12 else 0)
    stroke = Image.new("RGBA", (W, H), (92, 74, 52, 0))
    stroke.putalpha(alpha)
    return stroke


def count_outside(path: Path, mask: Image.Image) -> int:
    alpha = Image.open(path).convert("RGBA").getchannel("A")
    outside = ImageChops.subtract(alpha, mask)
    return sum(1 for v in outside.getdata() if v > 0)


def fit_raw(raw: Image.Image) -> Image.Image:
    raw = raw.convert("RGBA")
    rw, rh = raw.size
    scale = max(W / rw, H / rh)
    nw, nh = int(round(rw * scale)), int(round(rh * scale))
    resized = raw.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - W) // 2
    top = (nh - H) // 2
    return resized.crop((left, top, left + W, top + H))


def make_board(items: list[dict]) -> Path:
    thumb_w, thumb_h, label_h, gutter = 520, 630, 46, 26
    cols = 2
    rows = math.ceil(len(items) / cols)
    board = Image.new("RGBA", (cols * thumb_w + (cols + 1) * gutter, rows * (thumb_h + label_h) + (rows + 1) * gutter), (250, 248, 240, 255))
    draw = ImageDraw.Draw(board, "RGBA")
    fnt = label_font(22)
    for idx, item in enumerate(items):
        im = Image.open(item["preview"]).convert("RGBA")
        im.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gutter + (idx % cols) * (thumb_w + gutter)
        y = gutter + (idx // cols) * (thumb_h + label_h + gutter)
        draw.text((x, y), item["title"], fill=(62, 48, 38, 255), font=fnt)
        board.alpha_composite(im, (x + (thumb_w - im.width) // 2, y + label_h))
    path = OUT / "festive-ab5-styled-options-board.png"
    board.save(path)
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
        fitted = fit_raw(Image.open(raw))
        art = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        art.alpha_composite(fitted)
        art.putalpha(mask)
        art_path = OUT / f"{slug}-artwork.png"
        art.save(art_path)
        preview = paper((W, H), 42000 + idx)
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
                "method": "openai-subgen-reference-attached plus exact AB5 mask postprocess",
                "raw": str(raw),
                "artwork": str(art_path),
                "preview": str(preview_path),
                "production_raw": str(PROD / raw.name),
                "production_artwork": str(PROD / art_path.name),
                "production_preview": str(PROD / preview_path.name),
                "outside_alpha_pixels": outside[art_path.name],
            }
        )
    board = make_board(manifest)
    report = {
        "pass": len(manifest) == len(VARIANTS) and all(v == 0 for v in outside.values()),
        "style_gate": "reference-attached OpenAI generation before exact mask postprocess",
        "mask": str(MASK),
        "canvas_size": [W, H],
        "candidates": manifest,
        "board": str(board),
        "production_board": str(PROD / board.name),
        "outside_alpha_pixels": outside,
    }
    (OUT / "ab5-styled-verification-report.json").write_text(json.dumps(report, indent=2))
    (OUT / "ab5-styled-manifest.json").write_text(json.dumps({"candidates": manifest, "board": str(board)}, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
