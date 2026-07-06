#!/usr/bin/env python3
"""render_from_paths.py — clean artboard render from TRUE vector paths.

Replaces the Illustrator PNG export as master_spec.py's input. The PNG export
carried dashed strokes and raster aliasing, forcing fragile morphological
reconstruction (dash bridging → scallops; bbox fits → the r16c wide-anchor
incident). This renders the bezier paths exported by scratchpad/master_paths.jsx
(tasks/_templates/master_paths.json) as CONTINUOUS SOLID strokes in the exact
class colors master_spec.classify() expects — dashes disappear at the source,
curves are smooth at any resolution.

CLI: python3 scripts/render_from_paths.py --paths tasks/_templates/master_paths.json \
        --out scratchpad/artboard01_clean.png --scale 55.48
Then: python3 scripts/master_spec.py --render scratchpad/artboard01_clean.png ...
"""
from __future__ import annotations
import argparse, json
import numpy as np
from PIL import Image, ImageDraw

# stroke cmyk -> render RGB chosen to satisfy master_spec.classify() thresholds
CLASS_RGB = {
    (0, 0, 0, 100): (0, 0, 0),        # black die cuts
    (0, 90, 85, 0): (239, 62, 54),    # red forbidden
    (0, 50, 100, 0): (255, 140, 0),   # orange door anchor
    (0, 10, 95, 0): (255, 215, 0),    # yellow safe inset / envelopes
    (75, 0, 100, 0): (60, 170, 60),   # green top envelope
}


def bezier_pts(p0, c0, c1, p1, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, c0, c1, p1 = map(np.array, (p0, c0, c1, p1))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c0 +
            3 * (1 - t) * t ** 2 * c1 + t ** 3 * p1)


def sample_path(path):
    pts = path["points"]
    out = []
    n = len(pts)
    segs = n if path["closed"] else n - 1
    for i in range(segs):
        a, b = pts[i], pts[(i + 1) % n]
        out.append(bezier_pts(a["a"], a["r"], b["l"], b["a"]))
    return np.vstack(out) if out else np.zeros((0, 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default="tasks/_templates/master_paths.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=55.48, help="percent: px per pt * 100")
    a = ap.parse_args()

    d = json.load(open(a.paths))
    L, T, R, B = d["artboard"]
    s = a.scale / 100.0
    W, H = int(round((R - L) * s)), int(round((T - B) * s))
    im = Image.new("RGB", (W, H), (255, 255, 255))
    dr = ImageDraw.Draw(im)

    drawn = skipped = 0
    for p in d["paths"]:
        key = tuple(p["stroke_cmyk"]) if p["stroke_cmyk"] else None
        rgb = CLASS_RGB.get(key)
        if rgb is None:
            skipped += 1
            continue
        xy = sample_path(p)
        if len(xy) < 2:
            skipped += 1
            continue
        px = [((x - L) * s, (T - y) * s) for x, y in xy]  # y-up pts -> y-down px
        if p["closed"]:
            px.append(px[0])
        dr.line(px, fill=rgb, width=3, joint="curve")
        drawn += 1

    im.save(a.out)
    print(f"[render_from_paths] {drawn} paths drawn, {skipped} skipped -> {a.out} {W}x{H}")


if __name__ == "__main__":
    main()
