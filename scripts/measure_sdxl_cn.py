#!/usr/bin/env python3
"""MEASURE the geometry of a controlnet_sdxl_gen.py output against the EXACT SVG
masks it was generated from (same bbox->output mapping), and draw an overlay.

This is the measurement gate for the SDXL-CN route. It reuses svg_classify (the
authoritative parser) and rebuilds the SAME body/hole masks at the SAME source
rect that controlnet_sdxl_gen.py used, so the numbers describe exactly what was
generated — no whole-template-bounds mismatch.

Metrics:
  * region-IoU(painted, body)  : IoU of the painted (non-white) area vs the
    body region (outer_contour + paintable_region, minus holes). 1.0 = the model
    painted the whole intended region and nothing outside it.
  * coverage                   : painted fraction WITHIN the (carved) paint region.
  * opening_fill               : painted fraction of the FULL opening = outer
    contour minus only the genuinely-enclosed small holes (NOT the big saloon-flap
    cutouts). This is the metric region-IoU/coverage are BLIND to: a door whose
    facade tapers to a trapezoid scores region-IoU 1.0 (because the empty corners
    were carved into the region) but a LOW opening_fill (the corners are white).
  * corner_fill                : painted fraction of each outer-contour corner box
    (worst-corner reported). A trapezoid leaves the bottom corners white -> low.
  * outside_frac               : painted fraction OUTSIDE the body (bleed).
  * holes: per-hole painted fraction; holes "clear" if all <= --hole-tol.

--full-bleed (door/facade panel): excludes large saloon-flap/splay cutouts (height
fraction of the panel > --flap-hfrac) from the "opening" so the FULL rectangular
contour must be painted. Mirrors controlnet_sdxl_gen.py --full-bleed so the gen and
the gate agree on which cutouts are real openings.

Usage:
  measure_sdxl_cn.py CAND.png --svg SVG --bbox L,T,R,B \
      [--out-overlay OV.png] [--white 240] [--hole-tol 0.03] \
      [--full-bleed] [--flap-hfrac 0.45]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--bbox", help="L,T,R,B in SVG user units (default = body bounds)")
    ap.add_argument("--out-overlay", type=Path)
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("--white", type=int, default=240, help="pixel is 'painted' if any channel < this")
    ap.add_argument("--hole-tol", type=float, default=0.03, help="max painted fraction of a hole to count as clear")
    ap.add_argument("--full-bleed", action="store_true",
                    help="door/facade panel: exclude large flap/splay cutouts (taller than "
                         "--flap-hfrac of the panel) from the opening, so opening_fill measures "
                         "fill of the FULL rectangular contour. Mirrors the gen flag.")
    ap.add_argument("--flap-hfrac", type=float, default=0.45,
                    help="cutout taller than this fraction of the panel = structural flap "
                         "(not an opening) under --full-bleed. Default 0.45.")
    a = ap.parse_args()

    cand = a.candidate if a.candidate.is_absolute() else ROOT / a.candidate
    svg = a.svg if a.svg.is_absolute() else ROOT / a.svg
    img = Image.open(cand).convert("RGB")
    W, H = img.size

    vb, shapes = C.extract_shapes(svg)
    shapes = C.classify(shapes)
    if a.bbox:
        L, T, R, Bm = (float(v) for v in a.bbox.split(","))
        src = (L, T, R - L, Bm - T)
    else:
        body = [s for s in shapes if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
        cx0 = min(s.bounds[0] for s in body); cy0 = min(s.bounds[1] for s in body)
        cx1 = max(s.bounds[2] for s in body); cy1 = max(s.bounds[3] for s in body)
        src = (cx0, cy0, cx1 - cx0, cy1 - cy0)
    min_x, min_y, bw, bh = src
    sx, sy = W / bw, H / bh
    f = lambda x, y: ((x - min_x) * sx, (y - min_y) * sy)

    # When a --bbox isolates ONE panel of a multi-panel template, keep only the
    # shapes that geometrically belong to that panel (centroid inside the crop),
    # so side-panel cutouts aren't mis-mapped into this crop and counted as
    # painted holes. Mirrors the same in_crop filter in controlnet_sdxl_gen.py.
    def in_crop(s):
        x0, y0, x1, y1 = s.bounds
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        return (min_x <= cx <= min_x + bw) and (min_y <= cy <= min_y + bh)

    sel = [s for s in shapes if s.polygon is not None and in_crop(s)] if a.bbox else \
          [s for s in shapes if s.polygon is not None]

    def is_flap(s):
        """Large structural saloon-flap/splay cutout (tall enough to read as the
        silhouette). Mirrors controlnet_sdxl_gen.is_flap so gen and gate agree."""
        x0, y0, x1, y1 = s.bounds
        return s.role == "internal_cutout" and (y1 - y0) / bh > a.flap_hfrac

    def fill(roles, predicate=None):
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        for s in sel:
            if s.role in roles and (predicate is None or predicate(s)):
                d.polygon([f(x, y) for x, y in s.polygon.exterior.coords], fill=255)
        return np.asarray(m) > 127

    body_m = fill(("outer_contour", "paintable_region"))
    # Under --full-bleed the big saloon-flap/splay cutouts are SUPPOSED to be painted
    # (the facade fills the contour), so the intended paint region carves only the
    # genuinely-enclosed SMALL holes. Otherwise (legacy) every cutout is carved. Using
    # the full-bleed region here keeps region-IoU + coverage meaningful: without it, a
    # correctly full-painted facade would score region-IoU LOW because the painted
    # flap area lands "outside" the (over-carved) region.
    if a.full_bleed:
        hole_m = fill(("internal_cutout",), predicate=lambda s: not is_flap(s))
    else:
        hole_m = fill(("internal_cutout",))
    region = body_m & ~hole_m  # intended paint region

    arr = np.asarray(img)
    painted = np.any(arr < a.white, axis=2)

    inter = int(np.sum(painted & region))
    union = int(np.sum(painted | region))
    iou = inter / union if union else 0.0
    region_px = int(np.sum(region))
    coverage = inter / region_px if region_px else 0.0
    outside = int(np.sum(painted & ~body_m))
    outside_frac = outside / max(1, int(np.sum(painted)))

    # OPENING-FILL: the metric region-IoU/coverage are blind to in the LEGACY path. The
    # "opening" = outer contour minus only the genuinely enclosed small holes. Under
    # --full-bleed it equals `region` above; in the legacy path (flaps carved) it
    # additionally un-carves the flaps so a tapered trapezoid (white corners) scores LOW
    # here even though it scored region-IoU 1.0 (the corners were carved into region).
    if a.full_bleed:
        opening = region
    else:
        small_hole_m = fill(("internal_cutout",), predicate=lambda s: not is_flap(s))
        opening = body_m & ~small_hole_m
    opening_px = int(np.sum(opening))
    opening_painted = int(np.sum(painted & opening))
    opening_fill = opening_painted / opening_px if opening_px else 0.0

    # CORNER probes: a trapezoid leaves the outer-contour CORNERS white. Probe a box in
    # each corner of the body bounding box (intersected with the opening so we only ask
    # about pixels that should be painted) and report the worst (least-filled) corner.
    ys, xs = np.where(body_m)
    corner_fill = {}
    worst_corner_fill = 1.0
    if len(xs):
        bx0, by0, bx1, by1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
        cbw = max(1, int(0.18 * (bx1 - bx0)))
        cbh = max(1, int(0.18 * (by1 - by0)))
        boxes = {
            "top-left":     (bx0, by0, bx0 + cbw, by0 + cbh),
            "top-right":    (bx1 - cbw, by0, bx1, by0 + cbh),
            "bottom-left":  (bx0, by1 - cbh, bx0 + cbw, by1),
            "bottom-right": (bx1 - cbw, by1 - cbh, bx1, by1),
        }
        for name, (x0c, y0c, x1c, y1c) in boxes.items():
            box_open = np.zeros((H, W), dtype=bool)
            box_open[y0c:y1c, x0c:x1c] = True
            box_open &= opening
            tot = int(np.sum(box_open))
            pf = int(np.sum(painted & box_open)) / tot if tot else 1.0
            corner_fill[name] = round(pf, 4)
        # the dome top legitimately curves inward; the TAPER bug is the bottom corners,
        # so the gate's "worst corner" focuses on the bottom pair.
        worst_corner_fill = round(min(corner_fill["bottom-left"], corner_fill["bottom-right"]), 4)

    # Holes to keep CLEAR = enclosed openings. Under --full-bleed the big saloon-flap
    # cutouts are NOT openings (the facade paints over them), so they're excluded from
    # the holes-clear check — otherwise a correctly painted facade would fail it.
    cuts = [s for s in sel if s.role == "internal_cutout"
            and (not (a.full_bleed and is_flap(s)))]
    holes = []
    holes_clear = True
    for i, s in enumerate(cuts, 1):
        hm = fill_one = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(fill_one)
        d.polygon([f(x, y) for x, y in s.polygon.exterior.coords], fill=255)
        hmask = np.asarray(fill_one) > 127
        area = int(np.sum(hmask))
        bled = int(np.sum(painted & hmask))
        frac = bled / area if area else 0.0
        clear = frac <= a.hole_tol
        holes_clear = holes_clear and clear
        holes.append({"i": i, "area": area, "painted": bled, "frac": round(frac, 4), "clear": clear})

    if a.out_overlay:
        ov = img.copy()
        d = ImageDraw.Draw(ov, "RGBA")
        for s in shapes:
            if s.polygon is not None and s.role in ("outer_contour", "paintable_region"):
                pts = [f(x, y) for x, y in s.polygon.exterior.coords]
                d.line(pts + [pts[0]], fill=(0, 220, 0, 255), width=3)
        for h, s in zip(holes, cuts):
            pts = [f(x, y) for x, y in s.polygon.exterior.coords]
            # under --full-bleed the big flaps are SUPPOSED to be painted, so they're
            # not real holes — outline them faint cyan, not red.
            if a.full_bleed and is_flap(s):
                col = (0, 200, 220, 160)
            else:
                col = (0, 220, 0, 255) if h["clear"] else (235, 40, 40, 255)
            d.line(pts + [pts[0]], fill=col, width=3)
        # corner probe boxes: green if filled, red if white (taper). Visualizes the gate.
        if len(xs):
            for name, (x0c, y0c, x1c, y1c) in boxes.items():
                cf = corner_fill.get(name, 1.0)
                col = (0, 220, 0, 255) if cf >= 0.85 else (235, 40, 40, 255)
                d.rectangle([x0c, y0c, x1c, y1c], outline=col, width=3)
        op = a.out_overlay if a.out_overlay.is_absolute() else ROOT / a.out_overlay
        op.parent.mkdir(parents=True, exist_ok=True)
        ov.save(op)

    result = {
        "candidate": str(cand),
        "size": [W, H],
        "region_iou": round(iou, 4),
        "coverage": round(coverage, 4),
        "opening_fill": round(opening_fill, 4),
        "worst_corner_fill": worst_corner_fill,
        "corner_fill": corner_fill,
        "full_bleed": bool(a.full_bleed),
        "outside_frac": round(outside_frac, 4),
        "holes_clear": holes_clear,
        "n_holes": len(holes),
        "n_holes_clear": sum(1 for h in holes if h["clear"]),
        "worst_hole_frac": round(max((h["frac"] for h in holes), default=0.0), 4),
        "holes": holes,
    }
    print(json.dumps(result, indent=2))
    if a.json_out:
        jp = a.json_out if a.json_out.is_absolute() else ROOT / a.json_out
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
