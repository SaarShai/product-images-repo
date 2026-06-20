#!/usr/bin/env python3
"""Overlay panel geometry on a candidate painting for assessment.
LIME  = panel cut contour (from contour-mask.png)
ORANGE = required window region (from SVG <image> transform)
Mapping = non-uniform (candidate size vs SVG viewBox), matching the framing
the user judges on.
"""
import argparse, cv2, numpy as np
from PIL import Image

VB_W, VB_H = 1874.73, 4213.29
IMG_W, IMG_H = 902, 966
TX, TY, SC = 122.8306, 1572.2065, 0.8343
CONTOUR = "tasks/whole-panel-build/B4-princess-window/contour-mask.png"

ap = argparse.ArgumentParser()
ap.add_argument("--cand", required=True)
ap.add_argument("--out", required=True)
a = ap.parse_args()

cand = cv2.cvtColor(np.array(Image.open(a.cand).convert("RGB")), cv2.COLOR_RGB2BGR)
H, W = cand.shape[:2]

# lime contour from mask
m = np.array(Image.open(CONTOUR).convert("L").resize((W, H), Image.NEAREST))
edges = cv2.Canny((m > 127).astype(np.uint8) * 255, 50, 150)
edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), 1)
cand[edges > 0] = (0, 255, 0)  # BGR lime

# orange window box
sfx, sfy = W / VB_W, H / VB_H
x0 = int(TX * sfx); y0 = int(TY * sfy)
x1 = int((TX + IMG_W * SC) * sfx); y1 = int((TY + IMG_H * SC) * sfy)
cv2.rectangle(cand, (x0, y0), (x1, y1), (0, 140, 255), max(3, W // 220))  # BGR orange

cv2.imwrite(a.out, cand)
print(f"overlay -> {a.out}  window-box=({x0},{y0})-({x1},{y1})")
