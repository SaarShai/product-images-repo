#!/usr/bin/env python3
"""Step 6 gate: check a generated candidate against the exact SVG geometry.

Overlays the authoritative SVG contour + cutouts onto the candidate image and
measures whether the holes were kept empty and the silhouette was respected.
A mechanical PASS here is a necessary gate, NOT style approval (step 7 is that).

Usage:
  svg_geometry_check.py <candidate.png> --svg <template.svg> \
      [--bbox L,T,R,B] [--out-overlay PATH] [--report PATH] [--cutout-tol 0.03]

--bbox is where the panel sits inside the candidate image, in pixels
(default: the whole image). The SVG viewBox is mapped into that box.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify as C  # noqa: E402
import svg_geometry as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def mapper(viewbox, bbox):
    min_x, min_y, box_w, box_h = viewbox
    L, T, R, B = bbox
    sx = (R - L) / box_w
    sy = (B - T) / box_h

    def f(x, y):
        return (L + (x - min_x) * sx, T + (y - min_y) * sy)

    return f


def poly_px(poly: Polygon, f) -> list[tuple[float, float]]:
    return [f(x, y) for x, y in poly.exterior.coords]


def fill_mask(size, polys_px) -> np.ndarray:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    for pts in polys_px:
        d.polygon(pts, fill=255)
    return np.asarray(m) > 127


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--bbox", help="L,T,R,B panel region in candidate px (default whole image)")
    ap.add_argument("--out-overlay", type=Path)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--json-out", type=Path, help="write metrics as JSON here (for the test runner)")
    ap.add_argument("--cutout-tol", type=float, default=0.03, help="max painted fraction of a hole to still PASS")
    ap.add_argument("--white", type=int, default=240, help="a pixel is 'painted' if any channel < this")
    args = ap.parse_args()

    cand_path = args.candidate if args.candidate.is_absolute() else ROOT / args.candidate
    svg = args.svg if args.svg.is_absolute() else ROOT / args.svg
    img = Image.open(cand_path).convert("RGB")
    W, H = img.size
    bbox = tuple(float(v) for v in args.bbox.split(",")) if args.bbox else (0.0, 0.0, float(W), float(H))

    viewbox, shapes = C.extract_shapes(svg)
    shapes = C.classify(shapes)

    body = [s for s in shapes if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
    cuts = [s for s in shapes if s.polygon is not None and s.role == "internal_cutout"]

    # Register by the CONTOUR, not the viewBox. auto_bbox detects the painted panel
    # = the outer contour; mapping the full viewBox onto it injects a scale+offset
    # error whenever the contour does not fill the viewBox (it usually doesn't).
    if body:
        cx0 = min(s.bounds[0] for s in body)
        cy0 = min(s.bounds[1] for s in body)
        cx1 = max(s.bounds[2] for s in body)
        cy1 = max(s.bounds[3] for s in body)
        src = (cx0, cy0, cx1 - cx0, cy1 - cy0)
    else:
        src = viewbox
    f = mapper(src, bbox)

    arr = np.asarray(img)
    painted = np.any(arr < args.white, axis=2)  # non-white pixel = paint/ink
    white = np.all(arr >= args.white, axis=2)  # near-white pixel = candidate opening

    contour_mask = fill_mask((W, H), [poly_px(s.polygon, f) for s in body])
    # subtract holes from the allowed-body mask
    holes_mask = fill_mask((W, H), [poly_px(s.polygon, f) for s in cuts]) if cuts else np.zeros((H, W), bool)
    allowed = contour_mask & ~holes_mask

    outside_painted = int(np.sum(painted & ~contour_mask))
    rows = []
    overall_fail = False
    ious = []
    for i, s in enumerate(cuts, 1):
        pxs = poly_px(s.polygon, f)
        hm = fill_mask((W, H), [pxs])
        area = int(np.sum(hm))
        bled = int(np.sum(painted & hm))
        frac = bled / area if area else 0.0
        # white-region IoU within a 50%-dilated bbox: did the model leave THIS
        # opening white at THIS location (positional adherence, not just bleed)?
        xs = [p[0] for p in pxs]
        ys = [p[1] for p in pxs]
        mw, mh = (max(xs) - min(xs)) * 0.5, (max(ys) - min(ys)) * 0.5
        rx0, ry0 = max(0, int(min(xs) - mw)), max(0, int(min(ys) - mh))
        rx1, ry1 = min(W, int(max(xs) + mw)), min(H, int(max(ys) + mh))
        region = np.zeros((H, W), bool)
        region[ry0:ry1, rx0:rx1] = True
        B = white & region
        inter = int(np.sum(hm & B))
        union = int(np.sum(hm | B))
        iou = inter / union if union else 0.0
        ious.append(iou)
        verdict = "PASS" if frac <= args.cutout_tol else "FAIL"
        if verdict == "FAIL":
            overall_fail = True
        rows.append((i, s.kind, [round(v, 1) for v in s.bounds], area, bled, round(frac, 3), round(iou, 3), verdict))

    # silhouette fit: paint outside the contour (model panel exceeds the shape)
    panel_px = int(np.sum(painted))
    outside_frac = outside_painted / max(1, panel_px)
    silhouette_fail = outside_frac > 0.02

    overlay_path = None
    if args.out_overlay:
        ov = img.copy()
        d = ImageDraw.Draw(ov, "RGBA")
        for s in body:
            d.line(poly_px(s.polygon, f) + [poly_px(s.polygon, f)[0]], fill=(0, 230, 0, 255), width=3)
        for i, s in enumerate(cuts, 1):
            col = (0, 230, 0, 255) if rows[i - 1][6] == "PASS" else (235, 40, 40, 255)
            pts = poly_px(s.polygon, f)
            d.line(pts + [pts[0]], fill=col, width=3)
        overlay_path = args.out_overlay if args.out_overlay.is_absolute() else ROOT / args.out_overlay
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        ov.save(overlay_path)

    lines = [
        "# Step 6 — geometry adherence check",
        "",
        f"candidate: `{rel(cand_path)}`",
        f"svg: `{rel(svg)}`   bbox: `{bbox}`",
        "",
        f"OVERALL: **{'FAIL' if (overall_fail or silhouette_fail) else 'PASS'}**  "
        f"(mechanical gate only — not style approval)",
        "",
        f"- silhouette: {outside_painted} painted px outside contour "
        f"({outside_frac:.1%} of panel paint) -> {'FAIL' if silhouette_fail else 'PASS'}",
        f"- mean opening IoU (model white vs exact opening): {(sum(ious)/len(ious)) if ious else 0:.3f}  "
        f"(1.0 = the model rendered each opening exactly on coordinate)",
        "",
        "| # | hole | bbox(svg) | hole px | painted px | painted frac | white-IoU | verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} |")
    report = "\n".join(lines) + "\n"
    print(report)
    if args.json_out:
        data = {
            "candidate": rel(cand_path),
            "overall": "FAIL" if (overall_fail or silhouette_fail) else "PASS",
            "outside_painted": outside_painted,
            "outside_frac": round(outside_frac, 4),
            "mean_iou": round(sum(ious) / len(ious), 4) if ious else 0.0,
            "holes": [{"i": r[0], "painted_frac": r[5], "iou": r[6], "verdict": r[7]} for r in rows],
        }
        jp = args.json_out if args.json_out.is_absolute() else ROOT / args.json_out
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(data, indent=2))
    if overlay_path:
        print(f"overlay -> {rel(overlay_path)}")
    if args.report:
        rp = args.report if args.report.is_absolute() else ROOT / args.report
        rp.parent.mkdir(parents=True, exist_ok=True)
        rp.write_text(report)
        print(f"report -> {rel(rp)}")
    return 1 if (overall_fail or silhouette_fail) else 0


if __name__ == "__main__":
    raise SystemExit(main())
