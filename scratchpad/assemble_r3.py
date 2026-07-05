#!/usr/bin/env python3
"""Assemble the 3-panel Marriott screen preview from finished RGBA panels,
placed at their true spec bbox positions in the shared viewbox."""
import json, pathlib
from PIL import Image

ROOT = pathlib.Path("/Users/za/Documents/product images repo")
G = ROOT / "tasks/marriott-hospital/geometry"
OUT = ROOT / "tasks/marriott-hospital/outputs"

specs = {p: json.load(open(G / f"{p}.spec.json")) for p in ("door", "left", "right")}
vb = specs["door"]["viewbox"]  # shared
CANVAS_W = 1600
sc = CANVAS_W / vb[2]
CANVAS_H = int(round(vb[3] * sc))

# soft neutral studio background (vertical light-grey gradient)
bg = Image.new("RGB", (CANVAS_W, CANVAS_H), (238, 238, 240))
px = bg.load()
for y in range(CANVAS_H):
    t = y / CANVAS_H
    v = int(244 - 26 * t)  # 244 -> 218
    for x in range(CANVAS_W):
        px[x, y] = (v, v, v + 2)

for p in ("left", "door", "right"):
    bb = specs[p]["bbox_svg"]
    x0 = int(round(bb[0] * sc)); y0 = int(round(bb[1] * sc))
    x1 = int(round(bb[2] * sc)); y1 = int(round(bb[3] * sc))
    w, h = x1 - x0, y1 - y0
    panel = Image.open(OUT / f"r3_{p}_final.png").convert("RGBA").resize((w, h), Image.LANCZOS)
    bg.paste(panel, (x0, y0), panel)

sp_png = OUT / "r3-screen-preview.png"
sp_jpg = OUT / "r3-screen-preview.jpg"
bg.save(sp_png); bg.save(sp_jpg, quality=92)
print(f"[assemble] {sp_jpg}  {CANVAS_W}x{CANVAS_H}", flush=True)
