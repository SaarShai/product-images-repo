#!/usr/bin/env python3
"""outset_cutouts.py — write a variant SVG whose INTERNAL cutouts are buffered
OUTWARD (outset) by N user-units, leaving the outer contour unchanged.

Why: model geometry drifts when generating an illustration. If the model is
told to leave an empty keep-clear area that is LARGER than the true cutout, the
real die-cut (original SVG) still falls inside empty paper even when the painted
hole drifts by a few points. This produces the GEOMETRY-stage outset; the prompt
route is the alternative STYLE-stage outset.

The outset shape is a buffered polygon (shapely) of the original cutout, sampled
from svg_geometry's path/polygon parser. Outer contour (largest area) is copied
verbatim. Everything keeps the original dashed keep-clear stroke style so the
report/render tools treat the outset ring exactly like the original opening.

  python3 scripts/outset_cutouts.py SRC.svg --out OUT.svg --outset 12
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import svg_geometry as G  # noqa: E402
try:
    from shapely.geometry import Polygon  # noqa: E402
except ImportError:
    print("This script requires /usr/bin/python3 (PATH python3 lacks shapely). Re-run with /usr/bin/python3.", file=sys.stderr)
    sys.exit(2)

STROKE = ('style="fill:none;stroke:#FFDB55;stroke-width:10;stroke-miterlimit:10;'
          'stroke-dasharray:24;"')


def poly_area(pts):
    p = Polygon(pts)
    return p.area if p.is_valid else Polygon(p).buffer(0).area


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--outset", type=float, default=12.0,
                    help="user-units to expand each cutout outward (default 12)")
    args = ap.parse_args()

    tmpl = G.read_template(args.svg)
    vb = tmpl.viewbox  # (minx, miny, w, h)

    # Collect every closed ring: (points, area). paths = list[list[subpaths]].
    rings = [r for r in tmpl.paths if len(r) >= 3]
    rings += [p for p in tmpl.polygons if len(p) >= 3]

    if not rings:
        print("no rings parsed", file=sys.stderr)
        return 1

    areas = [poly_area(r) for r in rings]
    outer_idx = max(range(len(rings)), key=lambda i: areas[i])

    parts = []
    for i, r in enumerate(rings):
        if i == outer_idx:
            pts = r
            kind = "outer (verbatim)"
        else:
            poly = Polygon(r)
            if not poly.is_valid:
                poly = poly.buffer(0)
            buffered = poly.buffer(args.outset, join_style=2)  # mitre
            pts = list(buffered.exterior.coords)
            kind = f"cutout outset +{args.outset}"
        pts_str = " ".join(f"{x:.4f},{y:.4f}" for x, y in pts)
        parts.append(f'<polygon {STROKE} points="{pts_str}"/>  <!-- {kind} -->')

    svg = (
        '<?xml version="1.0" encoding="iso-8859-1"?>\n'
        f'<svg version="1.1" xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" xml:space="preserve">\n'
        + "\n".join(parts) + "\n</svg>\n"
    )
    args.out.write_text(svg)
    print(f"wrote {args.out}  rings={len(rings)} outer_idx={outer_idx} "
          f"outset={args.outset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
