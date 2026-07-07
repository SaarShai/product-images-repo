#!/usr/bin/env python3
"""vector_spec.py — geometry contract from the TRUE vector paths (no raster).

Replaces master_spec.py's raster-reconstruction path. master_spec read a PNG
export of the artboard and rebuilt geometry with morphology (dilate/erode/close/
open + dash-bridging + bbox+semicircle synthesis). That caused: the jagged door
arch, the r16c synthetic wide-anchor, and dash leaks — and its heuristics were
co-tuned to the messy export, so they broke on clean input (v3 probe: body_frac
0.33 vs 0.92).

This reads tasks/_templates/master_paths.json (bezier paths exported straight
from the master .ai by master_paths.jsx) and renders CONTINUOUS SOLID strokes
per annotation class at any resolution. Because vector strokes are continuous
(dashes are just stroke STYLING over a real path), the silhouette flood needs no
morphological bridging — the single source of the whole family of bugs is gone.

Stroke CMYK -> class (from the census):
  (0,0,0,100)   black  die cuts (open = contour/slots, closed small = holes/rings)
  (0,90,85,0)   red    forbidden stripes (closed loops)
  (0,50,100,0)  orange door anchor (the arch; door panel only)
  (0,10,95,0)   yellow safe inset + hole keep-clear + adaptive-top envelope
  (75,0,100,0)  green  outer top envelope

Emits, per panel, into --outdir (same contract as master_spec.py):
  <p>-spec.json  <p>-mask.png  <p>-control.png  <p>-forbidden.png  <p>-holes.png

CLI: python3 scripts/vector_spec.py --paths tasks/_templates/master_paths.json \
        --scale 55.48 --outdir tasks/marriott-hospital/geometry/v3
"""
from __future__ import annotations

import argparse, json, sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]

# CMYK stroke key -> class name
CLASS = {
    (0, 0, 0, 100): "black",
    (0, 90, 85, 0): "red",
    (0, 50, 100, 0): "orange",
    (0, 10, 95, 0): "yellow",
    (75, 0, 100, 0): "green",
}

# panel x-extents in ARTBOARD pts (y-up), from the census/master_spec contract.
# y-window generous; true vertical extent detected from rendered black pixels.
PANELS_PTS = {
    "left":  (1187, 2841),
    "door":  (2875, 5905),
    "right": (5934, 7588),
    "stab1": (8981, 9424),
    "stab2": (9550, 9993),
}
ADAPTIVE_TOP = {"left", "door", "right"}  # dome tops close at the yellow envelope
STROKE_PX = 3  # rendered stroke width; continuous, so this is all the bridging needed
BODY_MIN_FRAC = 0.03  # interior region >= this frac of panel = paintable body, else hole


def bezier_pts(p0, c0, c1, p1, n=48):
    t = np.linspace(0, 1, n)[:, None]
    p0, c0, c1, p1 = map(np.array, (p0, c0, c1, p1))
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c0 +
            3 * (1 - t) * t ** 2 * c1 + t ** 3 * p1)


def sample_path(path):
    """Flatten a path's cubic segments to a dense polyline in pt space (y-up)."""
    pts = path["points"]
    n = len(pts)
    if n < 2:
        return np.array([p["a"] for p in pts], float)
    out = []
    segs = n if path["closed"] else n - 1
    for i in range(segs):
        a, b = pts[i], pts[(i + 1) % n]
        out.append(bezier_pts(a["a"], a["r"], b["l"], b["a"]))
    return np.vstack(out)


def path_class(p):
    key = tuple(p["stroke_cmyk"]) if p["stroke_cmyk"] else None
    return CLASS.get(key)


def components(mask):
    """4-neighbour connected components, largest first."""
    h, w = mask.shape
    seen = np.zeros_like(mask, bool)
    comps = []
    ys, xs = np.where(mask)
    for y0, x0 in zip(ys.tolist(), xs.tolist()):
        if seen[y0, x0]:
            continue
        comp = np.zeros_like(mask, bool)
        dq = deque([(y0, x0)])
        seen[y0, x0] = True
        while dq:
            y, x = dq.popleft()
            comp[y, x] = True
            for ny, nx in ((y+1, x), (y-1, x), (y, x+1), (y, x-1)):
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    dq.append((ny, nx))
        comps.append(comp)
    comps.sort(key=lambda c: c.sum(), reverse=True)
    return comps


def flood_exterior(blocked, seed_top_only=True):
    """Flood the exterior through non-blocked pixels -> exterior mask.
    The die-cut contour is ONE continuous strip across all panels, so a per-panel
    crop has no left/right/bottom wall (the panel connects to its neighbours and
    sits on the base). Sealing those crop edges and seeding the flood from the TOP
    border only means the exterior is just the region above the dome arc + the
    shoulder corners — exactly what master_spec achieved by column-cropping.
    blocked = the stroke walls. Continuous strokes mean no morphology needed."""
    h, w = blocked.shape
    ext = np.zeros_like(blocked)
    dq = deque()
    edges = [(0, x) for x in range(w)]
    if not seed_top_only:
        edges += [(h - 1, x) for x in range(w)] + \
                 [(y, 0) for y in range(h)] + [(y, w - 1) for y in range(h)]
    for y, x in edges:
        if not blocked[y, x] and not ext[y, x]:
            ext[y, x] = True; dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for ny, nx in ((y+1, x), (y-1, x), (y, x+1), (y, x-1)):
            if 0 <= ny < h and 0 <= nx < w and not blocked[ny, nx] and not ext[ny, nx]:
                ext[ny, nx] = True; dq.append((ny, nx))
    return ext


def build(paths_json, scale_pct, outdir):
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    doc = json.load(open(paths_json))
    L, T, R, B = doc["artboard"]  # pts, y-up
    s = scale_pct / 100.0

    # group paths by class with pre-sampled polylines in pt space
    grouped = {c: [] for c in ("black", "red", "orange", "yellow", "green")}
    for p in doc["paths"]:
        c = path_class(p)
        if c is None:
            continue
        grouped[c].append({"xy": sample_path(p), "closed": p["closed"]})

    def in_window(poly, x0_pt, x1_pt):
        cx = poly[:, 0].mean()
        return x0_pt <= cx <= x1_pt

    report = {}
    for name, (x0_pt, x1_pt) in PANELS_PTS.items():
        # collect this panel's paths per class
        sel = {c: [g for g in grouped[c] if in_window(g["xy"], x0_pt, x1_pt)]
               for c in grouped}
        if not sel["black"]:
            report[name] = {"error": "no black cuts in window"}; continue

        # panel px box: x from the panel window, y from the actual path extent
        allxy = np.vstack([g["xy"] for c in sel for g in sel[c]]) if any(sel.values()) else None
        # y-extent: union of black + (yellow top for adaptive) path bounds
        yext_src = list(sel["black"])
        if name in ADAPTIVE_TOP:
            yext_src += sel["yellow"] + sel["green"]
        ys_pt = np.concatenate([g["xy"][:, 1] for g in yext_src])
        y_top_pt, y_bot_pt = ys_pt.max(), ys_pt.min()  # y-up: top = max
        # black-only bottom (holes/rings don't extend below contour, but be safe)
        xb = np.concatenate([g["xy"][:, 0] for g in sel["black"]])
        x0b_pt, x1b_pt = xb.min(), xb.max()

        pad_pt = 8 / s  # ~8px margin
        px0_pt, px1_pt = x0b_pt - pad_pt, x1b_pt + pad_pt
        pyt_pt, pyb_pt = y_top_pt + pad_pt, y_bot_pt - pad_pt
        W = int(round((px1_pt - px0_pt) * s))
        Hh = int(round((pyt_pt - pyb_pt) * s))

        def to_px(xy):
            px = (xy[:, 0] - px0_pt) * s
            py = (pyt_pt - xy[:, 1]) * s  # y-up pt -> y-down px
            return np.stack([px, py], 1)

        def render(polys, closed_fill=False, width=STROKE_PX):
            img = Image.new("L", (W, Hh), 0)
            dr = ImageDraw.Draw(img)
            for g in polys:
                pts = [tuple(p) for p in to_px(g["xy"])]
                if len(pts) < 2:
                    continue
                if closed_fill and g["closed"]:
                    dr.polygon(pts, fill=255)
                else:
                    if g["closed"]:
                        pts = pts + [pts[0]]
                    dr.line(pts, fill=255, width=width, joint="curve")
            return np.array(img) > 127

        black = render(sel["black"])
        # walls that close the silhouette: black cuts + (adaptive) yellow/green top arc
        walls = black.copy()
        if name in ADAPTIVE_TOP:
            # only the ARC segments near the top close the dome; render yellow+green
            # top paths whose points reach into the upper region
            top_cut_px = int(Hh * 0.5)
            for src in ("yellow", "green"):
                for g in sel[src]:
                    pxy = to_px(g["xy"])
                    if pxy[:, 1].min() < top_cut_px:  # touches upper half
                        img = Image.new("L", (W, Hh), 0)
                        dr = ImageDraw.Draw(img)
                        p = [tuple(v) for v in pxy]
                        if g["closed"]:
                            p = p + [p[0]]
                        dr.line(p, fill=255, width=STROKE_PX + 1, joint="curve")
                        walls |= np.array(img) > 127

        # seal the crop's side/base borders: the die-cut is one continuous strip,
        # so a panel's side/base boundaries are the crop window, not real cuts
        # (master_spec did this by column-cropping).
        walls[:, 0] = True
        walls[:, -1] = True
        walls[-1, :] = True
        if name in ADAPTIVE_TOP:
            # domed panels: top is open, closed by the dome arc (yellow/green);
            # flood from the top border to carve out the above-arch exterior.
            ext = flood_exterior(walls, seed_top_only=True)
        else:
            # stabilizer strips: near-rectangular, contour is open on one side;
            # the bounding box IS the silhouette. Seal the top too — no exterior.
            walls[0, :] = True
            ext = flood_exterior(walls, seed_top_only=True)
        body = ~ext  # includes walls + interior + enclosed holes
        # Split interior into paintable body vs holes. The panel face is divided
        # into several LARGE regions by the slot cuts (e.g. the door splits into
        # left/centre/right thirds) — those are all paintable body. Only SMALL
        # enclosed regions (finger holes, circle cutouts) are holes. Classify by
        # area, not by "largest component" (that dropped 2 of the door's 3 thirds).
        interior = body & ~black
        area = W * Hh
        paint = np.zeros_like(body)
        holes = np.zeros_like(body)
        for c in components(interior):
            ys, xs = np.where(c)
            # phantom ring guard: the thin sliver between the sealed crop border
            # and the contour stroke is unreachable by the top flood, so it lands
            # in "interior". Signature: bbox spans nearly the whole frame but the
            # area is a sliver (fill ratio ~0). A stab panel's REAL body also
            # spans the frame but is solid — the fill-ratio condition spares it.
            bw, bh = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
            if bw > 0.8 * W and bh > 0.8 * Hh and c.sum() < 0.05 * bw * bh:
                continue  # padding artifact: neither paintable body nor a hole
            (paint if c.sum() >= BODY_MIN_FRAC * area else holes)[c] = True

        mask_img = ((paint | (black & body)) * 255).astype("uint8")
        mask_img[holes] = 0

        # control map: SOLID edges only. Outer boundary of the body + interior
        # black cuts. No morphology — strokes are already clean/continuous.
        outer = body & ~_erode1(body)
        ctrl = _dilate1(black) | outer
        if name == "door" and sel["orange"]:
            for g in sel["orange"]:  # the true smooth arch, rendered directly
                pts = [tuple(p) for p in to_px(g["xy"])]
                if len(pts) >= 2:
                    img = Image.new("L", (W, Hh), 0)
                    ImageDraw.Draw(img).line(pts, fill=255, width=STROKE_PX + 1, joint="curve")
                    ctrl |= np.array(img) > 127

        forb = render(sel["red"], closed_fill=True)

        Image.fromarray(mask_img).save(outdir / f"{name}-mask.png")
        Image.fromarray((ctrl * 255).astype("uint8")).convert("RGB").save(outdir / f"{name}-control.png")
        Image.fromarray((forb * 255).astype("uint8")).save(outdir / f"{name}-forbidden.png")
        Image.fromarray((holes * 255).astype("uint8")).save(outdir / f"{name}-holes.png")

        spec = {
            "panel": name, "source": "vector", "px_per_pt": round(s, 6),
            "box_px": [int(round((px0_pt - (L)) * s)), int(round((T - pyt_pt) * s)),
                       int(round((px1_pt - (L)) * s)), int(round((T - pyb_pt) * s))],
            "size_px": [W, Hh],
            "aspect": round(W / Hh, 4),
            "body_frac": round(float((mask_img > 127).mean()), 4),
            "holes_n": len([1 for c in components(holes) if c.sum() > 40]),
            "forbidden_bands_frac": _bands_frac(forb),
        }
        if name == "door" and sel["orange"]:
            oxy = np.vstack([g["xy"] for g in sel["orange"]])
            opx = to_px(oxy)
            spec["door_anchor_frac"] = [round(float(opx[:, 0].min() / W), 4),
                                        round(float(opx[:, 1].min() / Hh), 4),
                                        round(float(opx[:, 0].max() / W), 4),
                                        round(float(opx[:, 1].max() / Hh), 4)]
        json.dump(spec, open(outdir / f"{name}-spec.json", "w"), indent=1)
        report[name] = spec
    return report


def _dilate1(m):
    out = m.copy()
    out[1:, :] |= m[:-1, :]; out[:-1, :] |= m[1:, :]
    out[:, 1:] |= m[:, :-1]; out[:, :-1] |= m[:, 1:]
    return out


def _erode1(m):
    out = m.copy()
    out[1:, :] &= m[:-1, :]; out[:-1, :] &= m[1:, :]
    out[:, 1:] &= m[:, :-1]; out[:, :-1] &= m[:, 1:]
    return out


def _bands_frac(forb):
    fx = np.where(forb.any(axis=0))[0]
    if not len(fx):
        return []
    w = forb.shape[1]
    splits = np.where(np.diff(fx) > 8)[0]
    bands = [[round(b[0] / w, 4), round((b[-1] + 1) / w, 4)] for b in np.split(fx, splits + 1)]
    return [b for b in bands if b[1] - b[0] >= 0.02]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", default="tasks/_templates/master_paths.json")
    ap.add_argument("--scale", type=float, default=55.48, help="px per pt * 100")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    print(json.dumps(build(a.paths, a.scale, a.outdir), indent=1))


if __name__ == "__main__":
    main()
