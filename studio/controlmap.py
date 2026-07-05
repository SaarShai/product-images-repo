"""Packet-driven control-map builder for the one-pass geometry×style route.

Derives, from a panel spec (skyline_panel.py .spec.json) + its template SVG:
  <panel>-mask.png     silhouette mask (white = paintable body)
  <panel>-control.png  edge/control map for flux-control-lora-canny — the SVG's
                       solid CUT layer only, annotation dashes stripped

Why: hand-built guides carry annotation colors (keep-clear stripes, safe-area
dashes) that a canny control channel edge-detects into hard lines the model
paints as structures. The cut layer IS the perfect edge map. (Proven 2026-07-04:
ONEPASS-FINDINGS.md — content appears exactly where control edges are.)

Optional --content edges.json adds interior content edges (windows, sills) as
white outlines: [{"type":"rect|archwin|line","frac":[x0,y0,x1,y1]}] in panel
fractions. LAW 0 for the control channel: content that must appear needs edges.

CLI: python3 -m studio.controlmap --spec <panel.spec.json> --width 900 \
        --outdir <dir> [--content edges.json]
"""
from __future__ import annotations

import argparse, json, subprocess, tempfile
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent


def render_svg(svg_path, px_width):
    """Render SVG via rsvg-convert to RGBA numpy array."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp = f.name
    subprocess.run(["rsvg-convert", "-w", str(px_width), str(svg_path), "-o", tmp],
                   check=True)
    im = Image.open(tmp).convert("RGBA")
    return np.array(im)


def cut_layer(rgba):
    """Charcoal strokes (#231f20-ish) = cut geometry; drops colored dashes.

    Alpha threshold is LOW (30): hairline strokes rasterize sub-pixel with
    anti-aliased alpha far below 200 while keeping the stroke's rgb — an
    opaque-only filter silently loses the outer contours (bug found 2026-07-04).
    Colored annotation dashes (yellow/red/green/blue) have a high channel.
    """
    r, g, b, a = (rgba[..., i].astype(int) for i in range(4))
    return (a > 30) & (r < 120) & (g < 120) & (b < 120)


def _dilate(mask, it=2):
    """Non-wrapping binary dilation. np.roll wraps edges — bottom-row strokes
    would teleport onto row 0 and seal flood seeds (bug found 2026-07-04)."""
    m = mask.copy()
    for _ in range(it):
        up = np.zeros_like(m);    up[:-1]  = m[1:]
        dn = np.zeros_like(m);    dn[1:]   = m[:-1]
        lf = np.zeros_like(m);    lf[:, :-1] = m[:, 1:]
        rt = np.zeros_like(m);    rt[:, 1:]  = m[:, :-1]
        m = m | up | dn | lf | rt
    return m


def panel_silhouette(cut_crop, dilate_iters=3, close_bottom=True):
    """Per-panel flood-fill: body = pixels the outside flood can't reach.

    Run on the PANEL CROP, not the full template: die-cut panels have a
    straight bottom cut with no stroke (open floor), so we wall the crop's
    bottom row explicitly and seed the flood from the top corners, which for
    an arched/domed panel are always genuinely outside the contour.
    """
    closed = _dilate(cut_crop, dilate_iters)
    if close_bottom:
        closed[-2:, :] = True
    h, w = closed.shape
    reach = np.zeros_like(closed, bool)
    dq = deque()
    for y, x in ((0, 0), (0, w - 1)):
        if not closed[y, x]:
            reach[y, x] = True
            dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y+1, x), (y-1, x), (y, x+1), (y, x-1)):
            if 0 <= ny < h and 0 <= nx < w \
                    and not closed[ny, nx] and not reach[ny, nx]:
                reach[ny, nx] = True
                dq.append((ny, nx))
    return ~reach  # body, including the strokes themselves


def panel_box(shape, spec):
    h, w = shape[:2]
    vb = spec["viewbox"]; bb = spec["bbox_svg"]
    x0 = int(round((bb[0] - vb[0]) / vb[2] * w)); x1 = int(round((bb[2] - vb[0]) / vb[2] * w))
    y0 = int(round((bb[1] - vb[1]) / vb[3] * h)); y1 = int(round((bb[3] - vb[1]) / vb[3] * h))
    return max(y0, 0), min(y1, h), max(x0, 0), min(x1, w)


def panel_crop(arr2d_or_rgba, spec, pad=0):
    """Crop to the panel bbox. pad>0 widens the window (clamped) so hairline
    contour strokes sitting exactly ON the bbox edge aren't clipped away —
    a tight crop loses the side walls and the silhouette flood leaks in."""
    h, w = arr2d_or_rgba.shape[:2]
    y0, y1, x0, x1 = panel_box(arr2d_or_rgba.shape, spec)
    py0, px0 = max(y0 - pad, 0), max(x0 - pad, 0)
    py1, px1 = min(y1 + pad, h), min(x1 + pad, w)
    crop = arr2d_or_rgba[py0:py1, px0:px1]
    inner = (y0 - py0, y0 - py0 + (y1 - y0), x0 - px0, x0 - px0 + (x1 - x0))
    return crop, inner


def draw_content(draw, edges, w, h, width=5):
    for e in edges:
        x0, y0, x1, y1 = [c * (w if i % 2 == 0 else h) for i, c in enumerate(e["frac"])]
        if e["type"] == "rect":
            draw.rectangle([x0, y0, x1, y1], outline=255, width=width)
        elif e["type"] == "archwin":  # arched window:半circle top + straight sides + sill
            r = (x1 - x0) / 2
            draw.arc([x0, y0, x1, y0 + 2 * r], 180, 360, fill=255, width=width)
            draw.line([x0, y0 + r, x0, y1], fill=255, width=width)
            draw.line([x1, y0 + r, x1, y1], fill=255, width=width)
            draw.line([x0, y1, x1, y1], fill=255, width=width)
        elif e["type"] == "arch":  # open walkthrough: arc crown + legs to y1, NO sill
            r = (x1 - x0) / 2
            draw.arc([x0, y0, x1, y0 + 2 * r], 180, 360, fill=255, width=width)
            draw.line([x0, y0 + r, x0, y1], fill=255, width=width)
            draw.line([x1, y0 + r, x1, y1], fill=255, width=width)
        elif e["type"] == "line":
            draw.line([x0, y0, x1, y1], fill=255, width=width)


def erase_lanes(ctrl_img, lanes_frac, shrink=2):
    """Zero control edges inside keep-clear lane rects (spec keep_clear_lanes_frac).

    The guide renders lanes as a white slot with a dark border — those border
    edges leak into the control map and the model paints a literal column there
    (proven: Marriott round 1). The outer contour never crosses lane interiors,
    so erasing the rects is safe."""
    d = ImageDraw.Draw(ctrl_img)
    w, h = ctrl_img.size
    for ln in lanes_frac or []:
        # guides draw the lane slot wider than the spec rect — expand by ~3.5%
        # of panel width (plus `shrink` px) so the slot's border lines go too
        m = max(shrink, int(w * 0.035))
        x0 = max(ln["x0"] * w - m, 0); x1 = min(ln["x1"] * w + m, w)
        y0 = max(ln["y0"] * h - m, 0); y1 = min(ln["y1"] * h + m, h - 2)
        d.rectangle([x0, y0, x1, y1], fill=0)


def build(spec_path, px_width=1800, outdir=None, content_path=None):
    spec = json.load(open(spec_path))
    svg = REPO / spec["svg"] if not Path(spec["svg"]).is_absolute() else Path(spec["svg"])
    outdir = Path(outdir or Path(spec_path).parent)
    outdir.mkdir(parents=True, exist_ok=True)
    name = spec["panel"]

    rgba = render_svg(svg, px_width)
    cut_full = cut_layer(rgba)

    pad = max(6, px_width // 150)
    cut_pad, (iy0, iy1, ix0, ix1) = panel_crop(cut_full, spec, pad=pad)
    body_pad = panel_silhouette(cut_pad)
    cut = cut_pad[iy0:iy1, ix0:ix1]
    body = body_pad[iy0:iy1, ix0:ix1]

    mask_img = Image.fromarray((body * 255).astype("uint8"))
    # thicken hairline strokes so the control channel actually sees them
    ctrl = (_dilate(cut, 2) * 255).astype("uint8")
    ctrl_img = Image.fromarray(ctrl).convert("L")
    if content_path:
        d = ImageDraw.Draw(ctrl_img)
        draw_content(d, json.load(open(content_path)), ctrl_img.width, ctrl_img.height)
    # control map: white edges on black (canny convention)
    ctrl_rgb = Image.merge("RGB", [ctrl_img] * 3)

    mask_p = outdir / f"{name}-mask.png"
    ctrl_p = outdir / f"{name}-control.png"
    mask_img.save(mask_p); ctrl_rgb.save(ctrl_p)

    aspect = mask_img.width / mask_img.height
    report = {"panel": name, "mask": str(mask_p), "control": str(ctrl_p),
              "size": [mask_img.width, mask_img.height],
              "aspect": round(aspect, 4), "spec_aspect": spec["aspect"],
              "aspect_ok": abs(aspect - spec["aspect"]) <= spec.get("aspect_tol", 0.02),
              "body_frac": round(float(body.mean()), 4)}
    return report


def build_from_guide(guide_path, spec_path, outdir=None, content_path=None):
    """Derive mask + control map from a skyline_panel.py GUIDE png.

    Needed when the template SVG carries no drawn cut contour for a panel
    (the contour is synthesized by skyline_panel.py — its guide IS the
    authoritative pixel geometry; found 2026-07-04 on city-skyline template).
    Strips annotation colors (pink keep-clear stripes etc.): mask = everything
    not connected to the border through near-white; control = dark strokes only.
    """
    spec = json.load(open(spec_path))
    outdir = Path(outdir or Path(guide_path).parent)
    outdir.mkdir(parents=True, exist_ok=True)
    name = spec["panel"]

    arr = np.array(Image.open(guide_path).convert("RGB"))
    r, g, b = (arr[..., i].astype(int) for i in range(3))
    near_white = (r > 235) & (g > 235) & (b > 235)
    body = panel_silhouette(~near_white, dilate_iters=0, close_bottom=False)
    dark = (r < 120) & (g < 120) & (b < 120)  # bold contour + faint hints; drops pink/white
    ctrl_img = Image.fromarray((_dilate(dark, 1) * 255).astype("uint8")).convert("L")
    erase_lanes(ctrl_img, spec.get("keep_clear_lanes_frac"))
    if content_path:
        draw_content(ImageDraw.Draw(ctrl_img), json.load(open(content_path)),
                     ctrl_img.width, ctrl_img.height)
    ctrl_rgb = Image.merge("RGB", [ctrl_img] * 3)
    mask_img = Image.fromarray((body * 255).astype("uint8"))

    mask_p = outdir / f"{name}-mask.png"
    ctrl_p = outdir / f"{name}-control.png"
    mask_img.save(mask_p); ctrl_rgb.save(ctrl_p)
    aspect = mask_img.width / mask_img.height
    return {"panel": name, "mode": "from-guide", "mask": str(mask_p),
            "control": str(ctrl_p), "size": [mask_img.width, mask_img.height],
            "aspect": round(aspect, 4), "spec_aspect": spec["aspect"],
            "aspect_ok": abs(aspect - spec["aspect"]) <= spec.get("aspect_tol", 0.02),
            "body_frac": round(float(body.mean()), 4)}


def score(candidate_path, mask_path, iou_min=0.85, white=238):
    """Silhouette-IoU of a generated candidate vs a panel mask (CLI gate).

    Candidate is resized to the mask dims first — fal snaps image_size to
    buckets (e.g. 820x2105 -> 576x1536), so raw dims rarely match the mask.
    NOTE: this gate confirms SHAPE only, never content — a near-empty panel
    can still score >0.97 (Marriott r3 right_s1). Always pair with a VLM
    content/style judge. [[region-iou-not-fit-calibration]]
    """
    mask = np.array(Image.open(mask_path).convert("L")) > 127
    mh, mw = mask.shape
    img = Image.open(candidate_path).convert("RGB").resize((mw, mh), Image.NEAREST)
    a = np.array(img)
    r, g, b = (a[..., i].astype(int) for i in range(3))
    sil = panel_silhouette(~((r > white) & (g > white) & (b > white)),
                           dilate_iters=0, close_bottom=False)
    iou = float((sil & mask).sum()) / float((sil | mask).sum() or 1)
    return {"candidate": str(candidate_path), "mask": str(mask_path),
            "silhouette_iou": round(iou, 4), "iou_min": iou_min,
            "shape_pass": iou >= iou_min,
            "note": "shape only — vision judge still required"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec")
    ap.add_argument("--width", type=int, default=1800, help="full-template render width px")
    ap.add_argument("--outdir")
    ap.add_argument("--content", help="interior content edges json")
    ap.add_argument("--guide", help="derive from a skyline_panel guide PNG instead of the SVG cut layer")
    ap.add_argument("--score", help="candidate PNG to gate: --score cand.png --mask panel-mask.png")
    ap.add_argument("--mask", help="panel mask for --score")
    ap.add_argument("--iou-min", type=float, default=0.85)
    a = ap.parse_args()
    if a.score:
        if not a.mask:
            ap.error("--score requires --mask")
        print(json.dumps(score(a.score, a.mask, a.iou_min)))
    elif a.guide:
        if not a.spec:
            ap.error("--guide requires --spec")
        print(json.dumps(build_from_guide(a.guide, a.spec, a.outdir, a.content)))
    else:
        if not a.spec:
            ap.error("--spec required (or use --score)")
        print(json.dumps(build(a.spec, a.width, a.outdir, a.content)))


if __name__ == "__main__":
    main()
