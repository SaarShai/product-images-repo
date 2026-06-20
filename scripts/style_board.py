#!/usr/bin/env python3
"""Build a full-size side-by-side style-comparison board for HUMAN judging.

Given one or more REFERENCE style images and one or more CANDIDATE images, lay
them out in two labeled column-groups (REFERENCE on the left, CANDIDATE on the
right) on a single PNG. Images are kept LARGE and legible -- they are scaled to
a common, generous row height (default 1000px) WITHOUT downscaling to thumbnails,
so a human can actually judge brushwork, palette, bleed, and edge treatment.

CLI:
  python3 scripts/style_board.py --refs A.png[,B.png] --cands C.png[,D.png] --out board.png

Options:
  --refs    Comma-separated reference style image paths (required, >=1).
  --cands   Comma-separated candidate image paths (required, >=1).
  --out     Output PNG path (required).
  --height  Target per-image display height in px (default 1000). Images smaller
            than this are NOT upscaled past their native size unless --upscale.
  --upscale Allow upscaling small images up to --height (default off).
  --title   Optional board title text.

Deps: Pillow only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BG = (250, 250, 248)
INK = (20, 20, 20)
REF_BADGE = (40, 110, 60)
CAND_BADGE = (150, 60, 30)
DIVIDER = (150, 150, 150)

MARGIN = 28          # outer margin
GAP = 24             # gap between adjacent images
GROUP_GAP = 56       # gap between the REFERENCE group and the CANDIDATE group
CAP_H = 40           # per-image caption strip height
HEADER_H = 64        # column-group header height
TITLE_H = 44         # optional top title height


def load_font(size: int):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/Library/Fonts/Arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def parse_list(arg: str) -> list[Path]:
    out = []
    for tok in arg.split(","):
        tok = tok.strip()
        if not tok:
            continue
        out.append(Path(tok).expanduser())
    return out


def load_scaled(path: Path, target_h: int, upscale: bool):
    """Open image, scale to target_h height preserving aspect.

    Never downscales below the data unnecessarily: target_h is the common row
    height. If the native height is smaller and --upscale is off, the image is
    kept at native size (so we never invent detail), but it still sits in a row
    sized to target_h.
    """
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if h == target_h:
        return im
    if h > target_h or upscale:
        scale = target_h / float(h)
        new_w = max(1, round(w * scale))
        im = im.resize((new_w, target_h), Image.LANCZOS)
    return im


def text_w(draw, s, font) -> int:
    try:
        l, t, r, b = draw.textbbox((0, 0), s, font=font)
        return r - l
    except Exception:
        return draw.textlength(s, font=font) if hasattr(draw, "textlength") else len(s) * 8


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Full-size side-by-side style board for human judging.")
    ap.add_argument("--refs", required=True, help="Comma-separated reference image paths.")
    ap.add_argument("--cands", required=True, help="Comma-separated candidate image paths.")
    ap.add_argument("--out", required=True, help="Output PNG path.")
    ap.add_argument("--height", type=int, default=1000, help="Target per-image display height in px.")
    ap.add_argument("--upscale", action="store_true", help="Allow upscaling small images to --height.")
    ap.add_argument("--title", default="", help="Optional board title.")
    args = ap.parse_args(argv)

    ref_paths = parse_list(args.refs)
    cand_paths = parse_list(args.cands)
    if not ref_paths:
        print("error: --refs needs at least one path", file=sys.stderr)
        return 2
    if not cand_paths:
        print("error: --cands needs at least one path", file=sys.stderr)
        return 2

    missing = [str(p) for p in (ref_paths + cand_paths) if not p.exists()]
    if missing:
        print("error: missing input file(s):\n  " + "\n  ".join(missing), file=sys.stderr)
        return 2

    target_h = max(64, args.height)

    refs = [(p, load_scaled(p, target_h, args.upscale)) for p in ref_paths]
    cands = [(p, load_scaled(p, target_h, args.upscale)) for p in cand_paths]

    # Common row height = tallest image actually produced (handles small native imgs).
    row_h = max(im.height for _, im in (refs + cands))

    ref_w = sum(im.width for _, im in refs) + GAP * (len(refs) - 1)
    cand_w = sum(im.width for _, im in cands) + GAP * (len(cands) - 1)

    top = MARGIN + (TITLE_H if args.title else 0)
    header_y = top
    img_y = header_y + HEADER_H
    cap_y = img_y + row_h

    board_w = MARGIN + ref_w + GROUP_GAP + cand_w + MARGIN
    board_h = cap_y + CAP_H + MARGIN

    board = Image.new("RGB", (board_w, board_h), BG)
    d = ImageDraw.Draw(board)

    f_title = load_font(30)
    f_header = load_font(26)
    f_cap = load_font(18)

    if args.title:
        d.text((MARGIN, MARGIN), args.title, fill=INK, font=f_title)

    # group headers
    d.text((MARGIN, header_y + 14), f"REFERENCE  ({len(refs)})", fill=REF_BADGE, font=f_header)
    cand_x0 = MARGIN + ref_w + GROUP_GAP
    d.text((cand_x0, header_y + 14), f"CANDIDATE  ({len(cands)})", fill=CAND_BADGE, font=f_header)

    # vertical divider between the two groups
    div_x = MARGIN + ref_w + GROUP_GAP // 2
    d.line([(div_x, header_y), (div_x, cap_y + CAP_H)], fill=DIVIDER, width=2)

    def place_group(items, x0, badge):
        x = x0
        for p, im in items:
            # center each image vertically within row_h (small natives sit centered)
            oy = img_y + (row_h - im.height) // 2
            board.paste(im, (x, oy))
            # caption: filename, centered under the image, truncated to image width
            name = p.name
            tw = text_w(d, name, f_cap)
            while tw > im.width and len(name) > 6:
                name = name[:-4] + "…"
                tw = text_w(d, name, f_cap)
            tx = x + max(0, (im.width - tw) // 2)
            d.text((tx, cap_y + 8), name, fill=badge, font=f_cap)
            x += im.width + GAP

    place_group(refs, MARGIN, REF_BADGE)
    place_group(cands, cand_x0, CAND_BADGE)

    out = Path(args.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    board.save(out)
    print(f"wrote {out}  ({board.size[0]}x{board.size[1]})  "
          f"refs={len(refs)} cands={len(cands)} row_h={row_h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
