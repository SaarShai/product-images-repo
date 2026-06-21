#!/usr/bin/env python3
"""Auto-extract style-reference crops from a finished illustration.

LAW: reference beats prose. To drive image-gen toward an existing art style,
feed it actual in-style crops of a finished piece rather than a worded
description. This picks N varied, content-rich crops from one source image so
they can be handed to a generator as style references.

Method
------
* Grid-sample many candidate crops across the image (a dense grid of fixed-size
  windows). The crop size is a fraction of the short edge so it scales with the
  source.
* Score every candidate by visual interest = edge density + colour variance.
  Near-white / flat-sky crops score ~0 and are skipped via a coverage floor.
* Drop any candidate overlapping an --avoid box (keep-clear / dieline regions).
* Greedily keep the highest-scoring crops while enforcing spatial spread (a
  light overlap cap) so the N crops sample different parts of the artwork
  instead of clustering on one busy corner.
* Save crop_1..N.png plus a contact-sheet.png and print each bbox.

Deps: PIL, numpy (both already in the existing venv).

CLI
---
python3 scripts/style_packet.py --image IMG --out-dir DIR [--n 6]
        [--avoid x0,y0,x1,y1 ...] [--crop-frac 0.28] [--seed 0]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def parse_box(s: str):
    parts = [int(round(float(x))) for x in s.replace(" ", "").split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"--avoid box must be x0,y0,x1,y1 (got {s!r})")
    x0, y0, x1, y1 = parts
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def iou(a, b):
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / float(area_a + area_b - inter)


def overlaps(a, b):
    """True if rectangles share any area at all."""
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (ax1 <= bx0 or bx1 <= ax0 or ay1 <= by0 or by1 <= ay0)


def score_crop(rgb: np.ndarray, edge: np.ndarray, box):
    """Visual-interest score for a crop: edge density + colour variance."""
    x0, y0, x1, y1 = box
    sub = rgb[y0:y1, x0:x1].astype(np.float32)
    esub = edge[y0:y1, x0:x1].astype(np.float32)
    if sub.size == 0:
        return 0.0, 1.0
    # coverage = fraction of pixels that are NOT near-white (sky/page).
    nonwhite = (sub.min(axis=2) < 235).mean()
    edge_density = esub.mean() / 255.0
    colour_var = sub.std(axis=(0, 1)).mean() / 128.0  # ~0..1ish
    interest = 0.6 * edge_density + 0.4 * colour_var
    return interest, nonwhite


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--avoid", type=parse_box, nargs="*", default=[],
                    help="keep-clear boxes in source pixels: x0,y0,x1,y1")
    ap.add_argument("--crop-frac", type=float, default=0.28,
                    help="crop side as fraction of the image short edge")
    ap.add_argument("--min-coverage", type=float, default=0.45,
                    help="min non-white fraction to keep a crop")
    ap.add_argument("--max-overlap", type=float, default=0.30,
                    help="max IoU allowed between kept crops")
    args = ap.parse_args(argv)

    src = Path(args.image)
    if not src.exists():
        print(f"ERROR: image not found: {src}", file=sys.stderr)
        return 2
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    img = Image.open(src).convert("RGB")
    W, H = img.size
    rgb = np.asarray(img)
    edge = np.asarray(img.convert("L").filter(ImageFilter.FIND_EDGES))

    short = min(W, H)
    cs = max(32, int(round(short * args.crop_frac)))
    cs = min(cs, W, H)

    # Dense grid of candidate windows (50% step for overlap headroom).
    step = max(1, cs // 2)
    cands = []
    for y0 in range(0, max(1, H - cs + 1), step):
        for x0 in range(0, max(1, W - cs + 1), step):
            box = (x0, y0, x0 + cs, y0 + cs)
            cands.append(box)
    # ensure right/bottom edges are represented
    for y0 in (0, H - cs):
        for x0 in (0, W - cs):
            box = (max(0, x0), max(0, y0), max(0, x0) + cs, max(0, y0) + cs)
            if box not in cands:
                cands.append(box)

    scored = []
    for box in cands:
        if any(overlaps(box, av) for av in args.avoid):
            continue
        interest, cov = score_crop(rgb, edge, box)
        if cov < args.min_coverage:
            continue
        scored.append((interest, box))
    scored.sort(key=lambda t: t[0], reverse=True)

    kept = []
    for interest, box in scored:
        if len(kept) >= args.n:
            break
        if all(iou(box, kb) <= args.max_overlap for _, kb in kept):
            kept.append((interest, box))

    # Relax the spread constraint only if the grid was too sparse to fill N.
    if len(kept) < args.n:
        for interest, box in scored:
            if len(kept) >= args.n:
                break
            if box not in [b for _, b in kept]:
                kept.append((interest, box))

    if not kept:
        print("ERROR: no content-rich crops found (image too flat/white?)",
              file=sys.stderr)
        return 1

    print(f"image={src.name} size={W}x{H} crop={cs}px candidates={len(cands)} "
          f"kept={len(kept)}/{args.n}")
    crop_paths = []
    bboxes = []
    for i, (interest, box) in enumerate(kept, 1):
        x0, y0, x1, y1 = box
        crop = img.crop(box)
        p = out / f"crop_{i}.png"
        crop.save(p)
        crop_paths.append(p)
        bboxes.append(box)
        print(f"  crop_{i}: bbox=({x0},{y0},{x1},{y1}) "
              f"size={x1-x0}x{y1-y0} interest={interest:.3f}")

    # Contact sheet: thumbnails in a row-major grid with index labels.
    n = len(crop_paths)
    cols = min(3, n)
    rows = (n + cols - 1) // cols
    thumb = 256
    pad = 10
    cap = 22
    sheet_w = cols * thumb + (cols + 1) * pad
    sheet_h = rows * (thumb + cap) + (rows + 1) * pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    for idx, (p, box) in enumerate(zip(crop_paths, bboxes)):
        r, c = divmod(idx, cols)
        x = pad + c * (thumb + pad)
        y = pad + r * (thumb + cap + pad)
        t = Image.open(p).convert("RGB").resize((thumb, thumb))
        sheet.paste(t, (x, y))
        draw.text((x, y + thumb + 3),
                  f"crop_{idx+1}  {box[0]},{box[1]}-{box[2]},{box[3]}",
                  fill=(20, 20, 20), font=font)
    sheet_path = out / "contact-sheet.png"
    sheet.save(sheet_path)
    print(f"contact-sheet: {sheet_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
