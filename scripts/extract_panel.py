#!/usr/bin/env python3
"""Isolate ONE panel from a multi-panel authoring SHEET into its own single-panel SVG.

A Screenery authoring file is often a 2x2 (or N-up) sheet: several panel contours in one
viewBox, each with its own interior cutouts. The SVG-driven tools (svg_to_controlmap,
controlnet_inpaint_gen, controlnet_style_gen, judge_panel) all assume ONE panel, so they
must be fed a single-panel SVG — otherwise body = every panel and holes = every cutout.

This picks the panel (by --index over contour-area-sorted bodies, or the body containing
--point X,Y) and emits a new SVG whose viewBox is that panel's tight bbox, containing the
contour + ONLY the cutouts whose centroid lies inside the contour polygon. Coordinates are
re-based to the panel origin so downstream rasterizers get a tight canvas.

Emits polygon approximations (circles already become 48-gons in svg_classify) — fine for the
raster control-map / guide-line pipeline; this is intake, the user's Drive SVG is untouched.

  extract_panel.py SHEET.svg --out PANEL.svg [--index 0] [--point 800,2200] [--pad 40]
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import svg_classify as C  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--index", type=int, default=0, help="panel index, bodies sorted by area desc")
    ap.add_argument("--point", help="X,Y inside the wanted panel (overrides --index)")
    ap.add_argument("--pad", type=float, default=40.0)
    a = ap.parse_args()

    vb, shapes = C.extract_shapes(a.svg)
    cl = C.classify(shapes)
    bodies = [s for s in cl if s.role in ("outer_contour", "paintable_region") and s.polygon is not None]
    if not bodies:
        print("no body/contour shapes found", file=sys.stderr); return 2
    bodies.sort(key=lambda s: -s.area)

    if a.point:
        px, py = (float(v) for v in a.point.split(","))
        pt = Point(px, py)
        cand = [b for b in bodies if b.polygon.contains(pt)]
        contour = min(cand, key=lambda s: s.area) if cand else bodies[0]
    else:
        contour = bodies[a.index]

    poly = contour.polygon
    cutouts = [s for s in cl if s.role == "internal_cutout" and s.polygon is not None
               and poly.contains(s.polygon.centroid)]
    x0, y0, x1, y1 = poly.bounds
    x0 -= a.pad; y0 -= a.pad; x1 += a.pad; y1 += a.pad
    W, H = x1 - x0, y1 - y0

    def path_d(p):
        pts = list(p.exterior.coords)
        d = "M " + " L ".join(f"{x - x0:.2f},{y - y0:.2f}" for x, y in pts) + " Z"
        return d

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.2f} {H:.2f}" '
             f'width="{W:.2f}" height="{H:.2f}">',
             '<style>.cut{fill:none;stroke:#ed1f79;stroke-width:3}'
             '.hole{fill:none;stroke:#231f20;stroke-width:3}</style>',
             f'<path class="cut" d="{path_d(poly)}"/>']
    for s in cutouts:
        parts.append(f'<path class="hole" d="{path_d(s.polygon)}"/>')
    parts.append("</svg>")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(parts))
    print(f"panel[{a.index if not a.point else 'pt'}] contour-area={contour.area:.0f} "
          f"viewBox={W:.0f}x{H:.0f} cutouts={len(cutouts)} -> {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
