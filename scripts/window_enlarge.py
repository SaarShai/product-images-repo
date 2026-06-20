#!/usr/bin/env python3
"""Enlarge the embedded window on a finished panel painting.

Two subcommands:
  composite  - paste the exact window image (window-cut.png) onto a base painting
               at the SVG-geometry-true box (optionally scaled), feathered.
  outline    - draw the target window outline (arched) on a copy of the base,
               as an edit-guide for a gen model ("make the window this big").

Geometry comes from the SVG <image> transform, mapped to the base pixel size
(non-uniform sf to match the full-bleed framing the user judged on).
"""
import argparse, math
from PIL import Image, ImageDraw, ImageFilter

# SVG facts (panel02-window.svg)
VB_W, VB_H = 1874.73, 4213.29
IMG_W, IMG_H = 902, 966
TX, TY, SC = 122.8306, 1572.2065, 0.8343


def geo_box(base_w, base_h):
    """window <image> box in base pixels (non-uniform)."""
    sfx, sfy = base_w / VB_W, base_h / VB_H
    x0 = TX * sfx
    y0 = TY * sfy
    w = IMG_W * SC * sfx
    h = IMG_H * SC * sfy
    return x0, y0, w, h


def scaled_box(base_w, base_h, scale, dx, dy):
    x0, y0, w, h = geo_box(base_w, base_h)
    cx, cy = x0 + w / 2, y0 + h / 2
    w *= scale; h *= scale
    nx = cx - w / 2 + dx
    ny = cy - h / 2 + dy
    return int(round(nx)), int(round(ny)), int(round(w)), int(round(h))


def cmd_composite(a):
    base = Image.open(a.base).convert("RGBA")
    win = Image.open(a.window).convert("RGBA")
    bx, by, bw, bh = scaled_box(base.width, base.height, a.scale, a.dx, a.dy)
    win = win.resize((bw, bh), Image.LANCZOS)
    # feather the alpha edge so the paste is not a hard rectangle
    alpha = win.split()[3]
    if a.feather > 0:
        alpha = alpha.filter(ImageFilter.GaussianBlur(a.feather))
    win.putalpha(alpha)
    out = base.copy()
    out.alpha_composite(win, (bx, by))
    out.convert("RGB").save(a.out)
    print(f"composite -> {a.out}  box=({bx},{by},{bw},{bh}) scale={a.scale}")


def cmd_outline(a):
    base = Image.open(a.base).convert("RGB")
    bx, by, bw, bh = scaled_box(base.width, base.height, a.scale, a.dx, a.dy)
    d = ImageDraw.Draw(base)
    # arched-top rounded shape: rectangle body + semicircle top
    r = bw // 2
    top = by + r
    col = (255, 0, 0)
    lw = max(4, bw // 40)
    # arch (semicircle)
    d.arc([bx, by, bx + bw, by + 2 * r], 180, 360, fill=col, width=lw)
    # sides
    d.line([(bx, top), (bx, by + bh)], fill=col, width=lw)
    d.line([(bx + bw, top), (bx + bw, by + bh)], fill=col, width=lw)
    # bottom
    d.line([(bx, by + bh), (bx + bw, by + bh)], fill=col, width=lw)
    base.save(a.out)
    print(f"outline -> {a.out}  box=({bx},{by},{bw},{bh})")


p = argparse.ArgumentParser()
sub = p.add_subparsers(dest="cmd", required=True)
for name in ("composite", "outline"):
    s = sub.add_parser(name)
    s.add_argument("--base", required=True)
    s.add_argument("--out", required=True)
    s.add_argument("--scale", type=float, default=1.0)
    s.add_argument("--dx", type=float, default=0.0)
    s.add_argument("--dy", type=float, default=0.0)
    if name == "composite":
        s.add_argument("--window", required=True)
        s.add_argument("--feather", type=float, default=2.0)
a = p.parse_args()
{"composite": cmd_composite, "outline": cmd_outline}[a.cmd](a)
