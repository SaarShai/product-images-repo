#!/usr/bin/env python3
"""build_silhouette_base.py — contract base for panels whose boundary is split across
multiple OPEN paths (e.g. edge sockets/finger-joints drawn as a separate comb path).

build_trueaspect_base.py fills each path as its own polygon, so an OPEN edge path gets
closed endpoint-to-endpoint -> a spurious diagonal slash (np01-back-bottom-02 bug).
This builder instead treats EVERY subpath as a boundary STROKE, draws them all (a thick
stroke bridges small gaps where the comb meets the contour), flood-fills the exterior
from a corner, and the remaining interior is the true panel silhouette — socket notches
read as concavities in the edge, no interior holes, no slash.

  python3 scripts/build_silhouette_base.py SVG --out OUT.png [--canvas 1440x2560]
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import svg_geometry as G  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("svg", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--canvas", default="1440x2560")
    ap.add_argument("--body-color", default="232,228,220")
    ap.add_argument("--stroke", type=int, default=0, help="boundary stroke px (0=auto)")
    a = ap.parse_args()

    CW, CH = (int(v) for v in a.canvas.lower().split("x"))
    svg_path = a.svg if a.svg.is_absolute() else ROOT / a.svg
    t = G.read_template(svg_path)
    x0, y0, vbW, vbH = t.viewbox
    aspect = vbW / vbH
    ph = CH
    pw = round(ph * aspect)
    ox = (CW - pw) // 2
    sub = [p for p in t.paths if len(p) >= 2] + [p for p in t.polygons if len(p) >= 2]

    # svg_geometry skips <polyline>/<line> — parse them so edge segments close the boundary
    import xml.etree.ElementTree as ET
    for el in ET.parse(svg_path).getroot().iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "polyline" and el.attrib.get("points"):
            nums = [float(v) for v in el.attrib["points"].replace(",", " ").split()]
            pts = list(zip(nums[0::2], nums[1::2]))
            if len(pts) >= 2:
                sub.append(pts)
        elif tag == "line":
            try:
                sub.append([(float(el.attrib["x1"]), float(el.attrib["y1"])),
                            (float(el.attrib["x2"]), float(el.attrib["y2"]))])
            except KeyError:
                pass

    def to_px(x, y):
        return (ox + (x - x0) / vbW * pw, (y - y0) / vbH * ph)

    sw = a.stroke or max(3, round(pw / 110))  # thick enough to bridge comb->contour gaps
    # boundary mask: 255 on strokes
    bnd = Image.new("L", (CW, CH), 0)
    db = ImageDraw.Draw(bnd)
    for p in sub:
        pts = [to_px(x, y) for x, y in p]
        db.line(pts, fill=255, width=sw, joint="curve")
        for (px, py) in pts:  # round caps so corners close
            db.ellipse([px - sw/2, py - sw/2, px + sw/2, py + sw/2], fill=255)

    # flood-fill exterior from (0,0) over (not-boundary)
    from collections import deque
    px = bnd.load()
    ext = Image.new("L", (CW, CH), 0)
    ep = ext.load()
    dq = deque([(0, 0)])
    ep[0, 0] = 255
    while dq:
        x, y = dq.popleft()
        for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if 0 <= nx < CW and 0 <= ny < CH and ep[nx, ny] == 0 and px[nx, ny] == 0:
                ep[nx, ny] = 255
                dq.append((nx, ny))

    body_rgb = tuple(int(v) for v in a.body_color.split(","))
    canvas = Image.new("RGB", (CW, CH), "white")
    cp = canvas.load()
    for y in range(CH):
        for x in range(CW):
            if ep[x, y] == 0:  # interior or boundary = panel
                cp[x, y] = body_rgb

    out = a.out if a.out.is_absolute() else ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)
    print(f"wrote {out} {canvas.size}  paths={len(sub)} stroke={sw}px aspect={aspect:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
