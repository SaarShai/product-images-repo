#!/usr/bin/env python3
"""door_anchor_gate.py — painted-door vs door-anchor fit check (edge-alignment).

r16b incident: the painted door's arch was narrower than the anchor arch
("two arches") — invisible to silhouette-IoU and the fill gate. First version
of this gate measured blue-door pixels and was fragile (r13's compliant CREAM
stone surround didn't register). v2 is color-agnostic: walk the anchor PATH
(arc + straight sides from door_anchor_frac) and require a strong image edge
within --tol-frac of every path sample. Coverage < --min-cover ⇒ FAIL.

CLI: python3 scripts/door_anchor_gate.py --cand <img> --spec <door-spec.json> \
        [--overlay out.png] [--tol-frac 0.025] [--min-cover 0.85]
Exit 0 PASS / 2 FAIL (hard gate — this drift class shipped once already).
"""
from __future__ import annotations
import argparse, json, sys
import numpy as np
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--overlay", default=None)
    ap.add_argument("--tol-frac", type=float, default=0.025)
    ap.add_argument("--min-cover", type=float, default=0.85)
    a = ap.parse_args()

    spec = json.load(open(a.spec))
    ax0, ay0, ax1, ay1 = spec["door_anchor_frac"]
    im = Image.open(a.cand).convert("L")
    w, h = im.size
    # paper grain saturates a raw gradient (v2 calibration: coverage 1.0 on a
    # known-bad case). Smooth grain away first; keep only STRUCTURAL edges.
    from PIL import ImageFilter
    g = np.array(im.filter(ImageFilter.GaussianBlur(2.5))).astype(float)
    gx = np.abs(np.diff(g, axis=1, prepend=g[:, :1]))
    gy = np.abs(np.diff(g, axis=0, prepend=g[:1, :]))
    mag = gx + gy
    edges = mag > 14.0  # fixed structural threshold post-blur

    X0, X1 = int(ax0 * w), int(ax1 * w)
    Y0, Y1 = int(ay0 * h), int(ay1 * h)
    r_arch = (X1 - X0) / 2.0
    cx, cy = (X0 + X1) / 2.0, Y0 + r_arch
    tol = int(round(a.tol_frac * w))

    # sample the anchor path: semicircular arc + two straight sides
    pts = []
    for t in np.linspace(np.pi, 2 * np.pi, 120):           # arc (upper half)
        pts.append((cx + r_arch * np.cos(t), cy + r_arch * np.sin(t)))
    for y in np.linspace(cy, Y1, 60):
        pts.append((X0, y)); pts.append((X1, y))

    hit, miss_pts = 0, []
    for (px, py) in pts:
        x, y = int(round(px)), int(round(py))
        x0w, x1w = max(0, x - tol), min(w, x + tol + 1)
        y0w, y1w = max(0, y - tol), min(h, y + tol + 1)
        if edges[y0w:y1w, x0w:x1w].any():
            hit += 1
        else:
            miss_pts.append((x, y))
    cover = hit / len(pts)
    verdict = "PASS" if cover >= a.min_cover else "FAIL"

    if a.overlay:
        from PIL import ImageDraw
        ov = Image.open(a.cand).convert("RGB")
        d = ImageDraw.Draw(ov)
        d.arc([X0, Y0, X1, Y0 + int(2 * r_arch)], 180, 360, fill=(255, 0, 0), width=3)
        d.line([X0, int(cy), X0, Y1], fill=(255, 0, 0), width=3)
        d.line([X1, int(cy), X1, Y1], fill=(255, 0, 0), width=3)
        for (x, y) in miss_pts:
            d.ellipse([x - 4, y - 4, x + 4, y + 4], outline=(255, 0, 255), width=2)
        ov.save(a.overlay)

    print(json.dumps({"verdict": verdict, "edge_coverage": round(cover, 4),
                      "min_cover": a.min_cover, "tol_frac": a.tol_frac,
                      "miss_count": len(miss_pts), "overlay": a.overlay}, indent=1))
    sys.exit(0 if verdict == "PASS" else 2)


if __name__ == "__main__":
    main()
