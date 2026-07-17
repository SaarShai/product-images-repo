#!/usr/bin/env python3
"""Build a TRUE-aspect filled geometry base for subscription image-gen.

The panel viewBox is 1:3.393 (taller/narrower than any subscription aspect enum).
We render the outer contour (warm pale body) + internal cutouts (solid mid-grey
discs) at TRUE aspect, centered with WHITE side margins on a 9:16 canvas so the
panel fills full height. This makes the 9:16 enum CONGRUENT (no squish) and the
filled discs give the model an unambiguous opening contract (vs hollow lineart).

auto_bbox in geom_iou.py / geom_adherence_test.py recovers the panel region after
generation, so scoring is done on the de-letterboxed panel.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
try:
    import svg_classify as C  # noqa: E402
except ImportError:
    print("This script requires /usr/bin/python3 (PATH python3 lacks shapely). Re-run with /usr/bin/python3.", file=sys.stderr)
    sys.exit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--canvas", default="1440x2560", help="WxH of the letterbox canvas (9:16)")
    ap.add_argument("--body-color", default="232,228,220")
    ap.add_argument("--hole-color", default="128,128,128")
    a = ap.parse_args()

    CW, CH = (int(v) for v in a.canvas.lower().split("x"))
    vb, shapes = C.extract_shapes(a.svg if a.svg.is_absolute() else ROOT / a.svg)
    shapes = C.classify(shapes)
    body = [s for s in shapes if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
    cuts = [s for s in shapes if s.polygon is not None and s.role == "internal_cutout"]
    if not body:
        print("ERROR: no outer_contour/paintable body found", file=sys.stderr)
        return 1

    # viewBox extent (use SVG viewbox if present, else body bbox)
    cx0 = min(s.bounds[0] for s in body); cy0 = min(s.bounds[1] for s in body)
    cx1 = max(s.bounds[2] for s in body); cy1 = max(s.bounds[3] for s in body)
    vbW, vbH = (cx1 - cx0), (cy1 - cy0)
    aspect = vbW / vbH

    # panel fills full canvas height, true aspect, centered -> white side margins
    ph = CH
    pw = round(ph * aspect)
    ox = (CW - pw) // 2
    oy = 0
    print(f"panel {pw}x{ph} aspect={aspect:.4f} (1:{1/aspect:.3f}) margins_x={ox} on canvas {CW}x{CH}")

    def to_px(x, y):
        return (ox + (x - cx0) / vbW * pw, oy + (y - cy0) / vbH * ph)

    body_rgb = tuple(int(v) for v in a.body_color.split(","))
    hole_rgb = tuple(int(v) for v in a.hole_color.split(","))
    canvas = Image.new("RGB", (CW, CH), "white")
    d = ImageDraw.Draw(canvas)
    for s in body:
        d.polygon([to_px(x, y) for x, y in s.polygon.exterior.coords], fill=body_rgb)
    for s in cuts:
        d.polygon([to_px(x, y) for x, y in s.polygon.exterior.coords], fill=hole_rgb)

    out = a.out if a.out.is_absolute() else ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"wrote {out} {canvas.size}  body={len(body)} cuts={len(cuts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
