#!/usr/bin/env python3
"""overlay_board.py — review board of clean + overlay tile pairs (overlay law).

Geometry NEVER judged by eye alone: every candidate in the board is shown
BOTH as a clean tile and paired with an overlay tile (door-control.png lines
composited on top, after resizing the raw to the control's pixel dims), so a
reviewer always has the traced geometry line-up next to the plain result.
Labels (the raw's filename stem) sit in the gutter between each pair.

CLI:
  python3 scripts/overlay_board.py --raws '<glob>' --geom <geom-dir> \
      --out <board.jpg> [--panel door] [--cols 4] [--tile-w 320]

Note: quote the --raws glob so the shell doesn't expand it — this script
expands it itself via glob.glob so it works the same on any host.
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]


def load_font(size: int):
    for p in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def make_overlay_tile(raw: Image.Image, control: Image.Image) -> Image.Image:
    """Resize raw to control's pixel dims and composite control's traced
    lines on top in red (same convention as door_fill_gate.py's overlay)."""
    w, h = control.size
    resized = raw.convert("RGB")
    if resized.size != (w, h):
        resized = resized.resize((w, h), Image.Resampling.LANCZOS)
    ov = resized.convert("RGBA")

    control_np = np.array(control.convert("L"))
    lines_rgba = np.zeros((h, w, 4), dtype=np.uint8)
    lines_rgba[control_np > 60] = (255, 0, 0, 220)
    lines_img = Image.fromarray(lines_rgba)
    ov = Image.alpha_composite(ov, lines_img)
    return ov.convert("RGB")


def fit_tile(img: Image.Image, tile_w: int, tile_h: int) -> Image.Image:
    scale = min(tile_w / img.width, tile_h / img.height)
    resized = img.resize((round(img.width * scale), round(img.height * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (tile_w, tile_h), (255, 255, 255))
    left = (tile_w - resized.width) // 2
    top = (tile_h - resized.height) // 2
    canvas.paste(resized, (left, top))
    return canvas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raws", required=True, help="glob pattern for candidate raw PNGs (quote it)")
    ap.add_argument("--geom", required=True, help="geometry dir with <panel>-control.png")
    ap.add_argument("--panel", default="door")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=4, help="number of PAIR-columns per row")
    ap.add_argument("--tile-w", type=int, default=320)
    a = ap.parse_args()

    geom = Path(a.geom)
    control_path = geom / f"{a.panel}-control.png"
    control = Image.open(control_path)
    aspect = control.height / control.width
    tile_w = a.tile_w
    tile_h = round(tile_w * aspect)

    raw_paths = sorted(Path(p) for p in glob.glob(a.raws))
    if not raw_paths:
        print(f"no raws matched glob: {a.raws}", file=sys.stderr)
        return 1

    gutter = 28
    label_h = 26
    font = load_font(16)

    pair_w = tile_w * 2 + gutter
    pair_h = tile_h + label_h + gutter
    cols = a.cols
    rows = (len(raw_paths) + cols - 1) // cols

    board_w = cols * pair_w + (cols + 1) * gutter
    board_h = rows * pair_h + gutter
    board = Image.new("RGB", (board_w, board_h), (245, 245, 245))
    draw = ImageDraw.Draw(board)

    for i, raw_path in enumerate(raw_paths):
        row, col = divmod(i, cols)
        x0 = gutter + col * (pair_w + gutter)
        y0 = gutter + row * pair_h

        raw = Image.open(raw_path)
        clean_tile = fit_tile(raw.convert("RGB"), tile_w, tile_h)
        overlay_img = make_overlay_tile(raw, control)
        overlay_tile = fit_tile(overlay_img, tile_w, tile_h)

        board.paste(clean_tile, (x0, y0))
        board.paste(overlay_tile, (x0 + tile_w, y0))

        label = raw_path.stem
        draw.text((x0, y0 + tile_h + 4), label, fill=(20, 20, 20), font=font)

    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    board.convert("RGB").save(a.out, quality=92)
    print(f"wrote {a.out} ({len(raw_paths)} candidates, {cols}x{rows} grid)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
