#!/usr/bin/env python3
"""Render a clean ControlNet conditioning map from the authoritative SVG geometry.

Unlike a model-generated line-art map, this draws the *exact* template geometry
(outer contour + every cutout) as crisp black strokes on a white field, at a
caller-chosen pixel size that matches the SVG aspect ratio. This is what a
lineart / canny / scribble / mlsd ControlNet conditions on so generation can't
drift off the true coordinates.

The pixel box is mapped from the SVG viewBox the SAME way scripts/
svg_geometry_check.py maps it back, so a panel that fills the whole output image
is measured against these exact lines.

Usage:
  svg_to_controlmap.py SVG --out MAP.png --width 512 [--height H] \
      [--stroke 3] [--style lineart|canny] [--invert]

--style lineart : black lines on white  (control_v11p_sd15_lineart expects this)
--style canny   : white lines on black  (sd-controlnet-canny expects this)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify as C  # noqa: E402


def mapper(viewbox, W, H):
    min_x, min_y, box_w, box_h = viewbox
    sx = W / box_w
    sy = H / box_h

    def f(x, y):
        return (round((x - min_x) * sx), round((y - min_y) * sy))

    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("svg", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--width", type=int, default=512)
    ap.add_argument("--height", type=int, default=0, help="0 = derive from SVG aspect (multiple of 8)")
    ap.add_argument("--stroke", type=int, default=3)
    ap.add_argument("--style", choices=["lineart", "canny"], default="lineart")
    a = ap.parse_args()

    viewbox, shapes = C.extract_shapes(a.svg)
    shapes = C.classify(shapes)
    _, _, box_w, box_h = viewbox

    W = a.width
    if a.height:
        H = a.height
    else:
        H = int(round(W * box_h / box_w))
        H = H - (H % 8)  # multiple of 8 for the UNet
    f = mapper(viewbox, W, H)

    bg, fg = (255, 0)  # lineart: white bg, black lines
    if a.style == "canny":
        bg, fg = (0, 255)  # canny: black bg, white lines

    img = Image.new("L", (W, H), bg)
    d = ImageDraw.Draw(img)

    drawn = {"outer_contour": 0, "paintable_region": 0, "internal_cutout": 0}
    for s in shapes:
        if s.polygon is None:
            continue
        if s.role not in ("outer_contour", "paintable_region", "internal_cutout"):
            continue
        pts = [f(x, y) for x, y in s.polygon.exterior.coords]
        d.line(pts + [pts[0]], fill=fg, width=a.stroke, joint="curve")
        drawn[s.role] = drawn.get(s.role, 0) + 1

    out = a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(out)
    print(f"wrote {out}  size={W}x{H}  aspect={W/H:.4f}  style={a.style}  "
          f"contours={drawn['outer_contour']} paintable={drawn['paintable_region']} cutouts={drawn['internal_cutout']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
