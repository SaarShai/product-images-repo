#!/usr/bin/env python3
"""Trace a single-panel SILHOUETTE MASK (PNG) into a clean single-panel SVG (cut contour +
interior cutouts). The Screenery production masks (illustration-N.png where body=solid colour,
cutouts=holes) are unambiguous per-panel die-cut silhouettes — far cleaner to consume than
isolating a panel from a messy N-up authoring sheet. This makes every SVG-driven tool
(svg_to_controlmap, controlnet_inpaint_gen / _style_gen, punch_holes, judge_panel) work on a
mask-sourced panel with no other change.

Body detection (--body):
  magenta  : body = magenta pixels (mask-N.png: magenta body on white, white cutouts)
  nonblack : body = non-black pixels (painted-on-black renders)
  nonwhite : body = non-white pixels

Exterior background = body-complement region touching the image border; CUTOUTS = body-complement
regions NOT touching the border (truly enclosed). Contours via cv2, simplified with approxPolyDP.

  mask_to_svg.py --mask M.png --out PANEL.svg [--body magenta] [--pad 12] [--epsilon 1.5]
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import cv2


def body_of(im: np.ndarray, mode: str) -> np.ndarray:
    r, g, b = im[..., 0].astype(int), im[..., 1].astype(int), im[..., 2].astype(int)
    if mode == "magenta":
        return (r > 140) & (g < 130) & (b > 90) & (b < 210)
    if mode == "nonblack":
        return im.sum(2) > 60
    if mode == "nonwhite":
        return im.sum(2) < 735
    raise SystemExit(f"bad --body {mode}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mask", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--body", default="magenta", choices=["magenta", "nonblack", "nonwhite"])
    ap.add_argument("--pad", type=int, default=12)
    ap.add_argument("--epsilon", type=float, default=1.5, help="approxPolyDP epsilon (px)")
    ap.add_argument("--min-hole", type=int, default=40, help="drop cutouts smaller than this area px")
    a = ap.parse_args()

    im = np.asarray(Image.open(a.mask).convert("RGB"))
    body = body_of(im, a.body).astype(np.uint8)
    # clean specks
    body = cv2.morphologyEx(body, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    body = cv2.morphologyEx(body, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))

    # largest body component (the panel)
    n, lbl, stats, _ = cv2.connectedComponentsWithStats(body, 8)
    if n <= 1:
        raise SystemExit("no body found")
    panel_id = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    panel = (lbl == panel_id).astype(np.uint8)

    # outer contour of the panel
    cont, _ = cv2.findContours(panel, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    outer = max(cont, key=cv2.contourArea)
    outer = cv2.approxPolyDP(outer, a.epsilon, True).reshape(-1, 2)

    # cutouts = holes enclosed by the panel: complement regions not touching border, inside panel bbox
    comp = 1 - panel
    nh, hl, hstats, _ = cv2.connectedComponentsWithStats(comp, 8)
    H, W = panel.shape
    holes = []
    for i in range(1, nh):
        ys, xs = np.where(hl == i)
        if ys.min() == 0 or xs.min() == 0 or ys.max() == H - 1 or xs.max() == W - 1:
            continue  # touches border => exterior background
        if hstats[i, cv2.CC_STAT_AREA] < a.min_hole:
            continue
        hc, _ = cv2.findContours((hl == i).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        c = cv2.approxPolyDP(max(hc, key=cv2.contourArea), a.epsilon, True).reshape(-1, 2)
        if len(c) >= 3:
            holes.append(c)

    x0, y0 = outer[:, 0].min() - a.pad, outer[:, 1].min() - a.pad
    x1, y1 = outer[:, 0].max() + a.pad, outer[:, 1].max() + a.pad
    Wv, Hv = int(x1 - x0), int(y1 - y0)

    def d_of(poly):
        return "M " + " L ".join(f"{int(x - x0)},{int(y - y0)}" for x, y in poly) + " Z"

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {Wv} {Hv}" width="{Wv}" height="{Hv}">',
             '<style>.cut{fill:none;stroke:#ed1f79;stroke-width:3}'
             '.hole{fill:none;stroke:#231f20;stroke-width:3}</style>',
             f'<path class="cut" d="{d_of(outer)}"/>']
    for c in holes:
        parts.append(f'<path class="hole" d="{d_of(c)}"/>')
    parts.append("</svg>")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(parts))
    print(f"traced body({a.body}) viewBox={Wv}x{Hv} cutouts={len(holes)} verts(outer)={len(outer)} -> {a.out}")
    return 0


if __name__ == "__main__":
    from PIL import Image
    raise SystemExit(main())
