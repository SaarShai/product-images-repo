#!/usr/bin/env python3
"""r3 eval: silhouette-IoU per candidate vs panel mask + per-panel contact sheet."""
import sys, pathlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, "/Users/za/Documents/product images repo")
from studio.controlmap import panel_silhouette

ROOT = pathlib.Path("/Users/za/Documents/product images repo")
CM = ROOT / "tasks/marriott-hospital/geometry/controlmaps"
OUT = ROOT / "tasks/marriott-hospital/outputs"

def gen_silhouette(img):
    a = np.array(img.convert("RGB"))
    r, g, b = (a[..., i].astype(int) for i in range(3))
    near_white = (r > 238) & (g > 238) & (b > 238)
    return panel_silhouette(~near_white, dilate_iters=0, close_bottom=False)

def iou(a, b):
    return float((a & b).sum()) / float((a | b).sum() or 1)

results = {}
for panel in ("door", "left", "right"):
    mask = np.array(Image.open(CM / f"{panel}-mask.png").convert("L")) > 127
    mh, mw = mask.shape
    cells = []
    for i in (1, 2, 3):
        p = OUT / f"r3_{panel}_s{i}.png"
        img = Image.open(p)
        sil = gen_silhouette(img.resize((mw, mh), Image.NEAREST))
        v = iou(sil, mask)
        results[p.name] = v
        # contact cell: image scaled to h=560
        th = 560; tw = int(img.width / img.height * th)
        cell = img.convert("RGB").resize((tw, th))
        d = ImageDraw.Draw(cell)
        lab = f"{p.name}  IoU={v:.3f}"
        d.rectangle([0, 0, tw, 22], fill=(0, 0, 0))
        d.text((4, 5), lab, fill=(255, 255, 0))
        cells.append(cell)
    gap = 12
    W = sum(c.width for c in cells) + gap * (len(cells) + 1)
    H = max(c.height for c in cells) + 2 * gap
    sheet = Image.new("RGB", (W, H), (245, 245, 245))
    x = gap
    for c in cells:
        sheet.paste(c, (x, gap)); x += c.width + gap
    sp = OUT / f"r3-{panel}-sheet.jpg"
    sheet.save(sp, quality=90)
    print(f"[sheet] {sp.name}", flush=True)

print("\n=== silhouette-IoU ===", flush=True)
for k in sorted(results):
    flag = "  <-- LOW" if results[k] < 0.9 else ""
    print(f"  {k}: {results[k]:.3f}{flag}", flush=True)
