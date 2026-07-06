#!/usr/bin/env python3
"""master_spec.py — geometry contract v2 from the MASTER TEMPLATE artboard render.

Input: hi-res Illustrator export of artboard 1 (scratchpad/artboard01_hi.png,
scale recorded in the export log) + tasks/_templates/master_census.json (pts).
The render is the pixel truth for every annotation color:
  solid BLACK  = die cuts (contour, flaps, slots, finger holes, circle cutouts)
  RED dash     = forbidden stripes (over center stabilizer slots)
  ORANGE dash  = door anchor (door imagery sits exactly here)
  YELLOW dash  = 9.5mm safe inset + hole keep-clear rings (annotation only)
  GREEN dash   = adaptive top envelope (top contour may rise to here)

Emits, per panel (left / door / right / stab1 / stab2), into --outdir:
  <p>-spec.json       panel box (pts+px), aspect, zone fracs
  <p>-mask.png        silhouette (white = body) — flood-fill inside black contour
  <p>-control.png     control edges: black cuts (+ door anchor edges for door)
  <p>-forbidden.png   red forbidden stripes mask
  <p>-holes.png       enclosed cutout discs mask (for complement gate + bevel)

CLI: python3 scripts/master_spec.py --render scratchpad/artboard01_hi.png \
        --census tasks/_templates/master_census.json --scale 55.48 \
        --outdir tasks/marriott-hospital/geometry/v2
"""
from __future__ import annotations

import argparse, json, sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from studio.controlmap import _dilate, panel_silhouette  # noqa: E402

# panel x-extents in ARTBOARD pts (census-derived, y-up); artboard rect from census
PANELS_PTS = {
    # y-window is generous (dome arcs live in compound paths above the census
    # PathItem bboxes); true extent is detected from black pixels inside it
    "left":  (1187, 2841, 3450, -950),
    "door":  (2875, 5905, 3450, -950),
    "right": (5934, 7588, 3450, -950),
    "stab1": (8981, 9424, 3450, -950),
    "stab2": (9550, 9993, 3450, -950),
}


def classify(rgb):
    """Boolean masks per annotation color from the artboard render."""
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    black = (r < 90) & (g < 90) & (b < 90)
    red = (r > 170) & (g < 110) & (b < 110)
    orange = (r > 200) & (g > 90) & (g < 190) & (b < 90)
    yellow = (r > 200) & (g > 190) & (b < 120)
    green = (r < 160) & (g > 140) & (b < 140) & (g > r + 30)
    return {"black": black, "red": red, "orange": orange, "yellow": yellow, "green": green}


def bbox(mask):
    ys, xs = np.where(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def components(mask):
    """Connected components (4-neigh BFS). Returns list of boolean masks, largest first."""
    from collections import deque
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
                    seen[ny, nx] = True; dq.append((ny, nx))
        comps.append(comp)
    comps.sort(key=lambda c: c.sum(), reverse=True)
    return comps


def split_body_holes(body, cut):
    """The flood counts enclosed hole interiors as body. Split: largest
    open-region component = paintable body; smaller enclosed ones = holes."""
    open_region = body & ~cut
    comps = components(open_region)
    if not comps:
        return body, np.zeros_like(body)
    paint = comps[0]
    holes = np.zeros_like(body)
    for c in comps[1:]:
        holes |= c
    return paint, holes


def build(render_path, census_path, scale_pct, outdir):
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    census = json.load(open(census_path))
    ab = census["artboards"][0]["rect"]  # [L, T, R, B] pts, y-up
    px_per_pt = scale_pct / 100.0
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(render_path).convert("RGBA")
    bgw = Image.new("RGBA", im.size, (255, 255, 255, 255))
    rgb = np.array(Image.alpha_composite(bgw, im).convert("RGB"))  # PNG24 exports default to transparent bg
    H, W = rgb.shape[:2]
    masks = classify(rgb)

    def pt_to_px_x(x_pt):
        return int(round((x_pt - ab[0]) * px_per_pt))

    def pt_to_px_y(y_pt):  # render y grows downward from artboard TOP
        return int(round((ab[1] - y_pt) * px_per_pt))

    report = {}
    for name, (x0_pt, x1_pt, yt_pt, yb_pt) in PANELS_PTS.items():
        cx0, cx1 = max(pt_to_px_x(x0_pt) - 14, 0), min(pt_to_px_x(x1_pt) + 14, W)
        col = {k: v[:, cx0:cx1] for k, v in masks.items()}
        # vertical extent from the census panel box (auto-detect caught stray
        # off-panel black content far below the panels)
        wy0 = max(pt_to_px_y(yt_pt), 0)
        wy1 = min(pt_to_px_y(yb_pt), H)
        rows = np.where(col["black"][wy0:wy1].any(axis=1))[0]
        if not len(rows):
            report[name] = {"error": "no cuts found"}; continue
        shoulder = wy0 + rows.min()          # topmost BLACK cut row (dome shoulders)
        cy0 = max(shoulder - 6, 0)
        adaptive_top = name in ("left", "door", "right")
        if adaptive_top:
            # the dome TOP has NO fixed cut — only YELLOW (inner) / GREEN (outer)
            # envelope arcs; default contract closes the silhouette at YELLOW
            yrows = np.where(col["yellow"][wy0:wy1].any(axis=1))[0]
            if len(yrows):
                cy0 = max(wy0 + yrows.min() - 6, 0)
        cy1 = min(wy0 + rows.max() + 7, H)
        black_cut = col["black"][cy0:cy1].copy()
        # the template also carries BLACK DASHED guide strokes (e.g. along the
        # stabilizer-slot stripes) — annotation, not cuts, and dashes leak into
        # generated art as dot marks (user, turn 66). Real cuts are long
        # connected strokes / hole rings; dash segments are tiny blobs — drop them.
        for comp in components(black_cut):
            if comp.sum() < 300:
                black_cut &= ~comp
        cut = black_cut.copy()
        if adaptive_top:
            rel_sh = shoulder - cy0
            ydome = col["yellow"][cy0:cy1].copy()
            ydome[rel_sh + 10:] = False       # keep only the arc ABOVE the shoulders
            cut |= _dilate(ydome, 6)          # bridge the DASH gaps or the flood leaks
        # morphological CLOSE before flooding: the yellow arc (inset 9.5mm) does
        # not touch the side walls — ~15px gaps at both landings leak the flood
        big = _dilate(cut, 14)
        closed = ~_dilate(~big, 14)
        body = panel_silhouette(closed, dilate_iters=0, close_bottom=True)
        paint, holes = split_body_holes(body, cut)
        body_solid = body
        ph, pw = cut.shape

        mask_img = ((paint | cut & body) * 255).astype("uint8")  # paintable incl. stroke band, minus holes
        mask_img[holes] = 0
        # control map: SOLID edges only — dashed annotation strokes leak into the
        # art as painted dot marks (user, turn 66). Outer contour = the smooth
        # boundary of the closed silhouette (covers the adaptive dome top);
        # interior edges = the true black die cuts.
        # close (fill dash notches) then open (shave dash bumps): the dome top was
        # bridged from dashes and scallops in both directions
        body_smooth = ~_dilate(~_dilate(body, 9), 9)
        body_smooth = _dilate(~_dilate(~body_smooth, 7), 7)
        outer_edge = body_smooth & ~(~_dilate(~body_smooth, 2))
        ctrl = _dilate(black_cut, 2) | outer_edge
        if name == "door":
            # orange door anchor: trace the TRUE dashed path (r16c incident —
            # a synthetic bbox+semicircle arch was WIDER than the template's
            # real shape because stray orange dashes near the panel edges
            # inflated the percentile bbox). Method: close the dashes into one
            # curve, keep the LARGEST connected component only (strays are
            # small), then fill its closed outline and take the boundary.
            oz = col["orange"][cy0:cy1]
            if oz.sum() > 50:
                # keep the largest connected orange structure (strays are small)
                main = components(_dilate(oz, 30))[0]
                opix = main & _dilate(oz, 2)
                oy2, ox2 = np.where(opix)
                # ANALYTIC fit (morphological smoothing of a thin traced path
                # proved unstable): measure sides + crown from the pixels, draw
                # a clean arc + straight sides at the TRUE positions.
                y_top, y_bot = int(oy2.min()), int(oy2.max())
                lower = oy2 > (y_top + (y_bot - y_top) * 0.55)
                xL = int(np.median([ox2[lower & (ox2 < np.median(ox2))].min()
                                    if (lower & (ox2 < np.median(ox2))).any() else ox2.min()]))
                xL = int(np.percentile(ox2[lower], 1))
                xR = int(np.percentile(ox2[lower], 99))
                r_true = (xR - xL) / 2.0
                spring_y = y_top + r_true               # crown at y_top
                from PIL import ImageDraw
                arch = Image.new("L", (cut.shape[1], cut.shape[0]), 0)
                dr = ImageDraw.Draw(arch)
                dr.arc([xL, y_top, xR, int(y_top + 2 * r_true)], 180, 360, fill=255, width=4)
                dr.line([xL, int(spring_y), xL, y_bot], fill=255, width=4)
                dr.line([xR, int(spring_y), xR, y_bot], fill=255, width=4)
                dr.line([xL, y_bot, xR, y_bot], fill=255, width=4)
                ctrl = ctrl | (np.array(arch) > 127)
        forb = col["red"][cy0:cy1]
        # forbidden stripes as filled boxes (dashes -> solid): per connected x-band
        fx = np.where(forb.any(axis=0))[0]
        forb_solid = np.zeros_like(forb)
        if len(fx):
            splits = np.where(np.diff(fx) > 8)[0]
            bands = np.split(fx, splits + 1)
            for band in bands:
                bys = np.where(forb[:, band[0]:band[-1] + 1].any(axis=1))[0]
                if len(bys):
                    forb_solid[bys.min():bys.max() + 1, band[0]:band[-1] + 1] = True

        Image.fromarray(mask_img).save(outdir / f"{name}-mask.png")
        Image.fromarray((ctrl * 255).astype("uint8")).convert("RGB").save(outdir / f"{name}-control.png")
        Image.fromarray((forb_solid * 255).astype("uint8")).save(outdir / f"{name}-forbidden.png")
        Image.fromarray((holes * 255).astype("uint8")).save(outdir / f"{name}-holes.png")

        spec = {
            "panel": name, "px_per_pt": px_per_pt,
            "box_px": [int(cx0), int(cy0), int(cx1), int(cy1)], "size_px": [int(pw), int(ph)],
            "aspect": round(pw / ph, 4),
            "body_frac": round(float((mask_img > 127).mean()), 4),
            "holes_n": len([1 for c in components(holes) if c.sum() > 40]),
            "forbidden_bands_frac": _bands_frac(forb_solid),
            "green_top_frac": _zone_frac(col["green"][max(rows.min()-int(1200*px_per_pt),0):cy1], pw),
        }
        if name == "door":
            # anchor bbox from the LARGEST connected orange structure only —
            # global percentiles spanned stray edge dashes (r16c incident)
            oz2 = col["orange"][cy0:cy1]
            if oz2.sum() > 50:
                main2 = components(_dilate(oz2, 30))[0]
                oy, ox = np.where(main2 & _dilate(oz2, 2))
                spec["door_anchor_frac"] = [round(ox.min()/pw, 4), round(oy.min()/ph, 4),
                                            round(ox.max()/pw, 4), round(oy.max()/ph, 4)]
        json.dump(spec, open(outdir / f"{name}-spec.json", "w"), indent=1)
        report[name] = spec
    return report


def _has_scipy():
    try:
        import scipy.ndimage  # noqa
        return True
    except ImportError:
        return False


def _bands_frac(forb_solid):
    fx = np.where(forb_solid.any(axis=0))[0]
    if not len(fx):
        return []
    w = forb_solid.shape[1]
    splits = np.where(np.diff(fx) > 8)[0]
    bands = [[round(b[0]/w, 4), round((b[-1]+1)/w, 4)] for b in np.split(fx, splits + 1)]
    return [b for b in bands if b[1] - b[0] >= 0.02]  # drop anti-alias slivers


def _zone_frac(zone, pw):
    b = bbox(zone)
    return None if b is None else round((b[3] - b[1]) / zone.shape[0], 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", default="scratchpad/artboard01_hi.png")
    ap.add_argument("--census", default="tasks/_templates/master_census.json")
    ap.add_argument("--scale", type=float, required=True, help="export scale pct (from export log)")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    print(json.dumps(build(a.render, a.census, a.scale, a.outdir), indent=1))


if __name__ == "__main__":
    main()
