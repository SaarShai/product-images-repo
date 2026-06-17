#!/usr/bin/env python3
"""GUARANTEED-EXACT re-seat compositor: place openings at exact SVG coordinates
with an ILLUSTRATED (not flat code-punch) bevel rim, while PRESERVING the rest
of the model's painting (body, control hardware, knobs, sliders, dots, dashes).

Takes a model-generated panel (great watercolor look + rich controls, but
DRIFTED openings) and re-seats every opening at its exact SVG coordinate. Around
each exact edge we PAINT a BOLD hand-illustrated bevel: a dark-navy inner shadow
on the upper-left arc and a pale lit lip on the lower-right arc, gaussian-
feathered and slightly irregular so it reads watercolor, not vector.

DESIGN (v2 — controls-preserving): every destructive edit is CONFINED to a small
window around each exact opening. We do NOT scan the whole body for "drifted"
pale patches (that erased the controls in v1). Instead, per opening:
  - inside the exact aperture: pale clear + bold bevel rim;
  - in a tight ring just OUTSIDE the exact aperture: cover ONLY the model's own
    drifted version of THAT opening (its bright fill + its dark rim) with body-
    toned watercolor, because the drift is always local to the exact opening.
Everything beyond that local window (the full body, all controls/hardware) is
copied through UNTOUCHED.

Why a bevel and not a flat white punch: the user explicitly rejected the flat
white punch. A flat fill is geometrically exact but looks die-cut; the feathered
asymmetric rim makes the exact opening read as a painted recess in the panel.

Pipeline:
  1. Map SVG viewBox -> panel px (auto-detect the panel bbox, same convention as
     svg_geometry_check: the viewBox is mapped affine into [L,T,R,B]).
  2. Clear everything outside the outer contour to white (silhouette = exact).
  3. For each internal_cutout: locally cover the drifted opening (LOCAL window
     only) + pale interior + bold illustrated bevel rim.
  4. Write the exact-geometry illustration; the body + controls survive.

Usage:
  exact_bevel_composite.py --art ART.png --svg TEMPLATE.svg \
      [--bbox L,T,R,B] --out OUT.png [--debug-overlay PATH] \
      [--rim-scale 1.4] [--no-local-erase]

--bbox defaults to the auto-detected non-white panel bounds of --art.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import distance_transform_edt, gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import svg_classify as C  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def auto_bbox(arr: np.ndarray, white: int = 240) -> tuple[int, int, int, int]:
    """Panel bounds = bbox of the non-white region (matches geom_adherence_test)."""
    nonwhite = np.any(arr < white, axis=2)
    ys, xs = np.where(nonwhite)
    if len(xs) == 0:
        h, w = arr.shape[:2]
        return (0, 0, w, h)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def blue_body_bbox(arr: np.ndarray):
    """Panel-body bounds from the BLUE watercolor wash only.

    The plain non-white auto_bbox is polluted by hardware that sticks OUT past
    the panel body — cream knobs with radial tick marks, sliders, and capsule
    toggles painted overhanging the cobalt slab. That inflates the detected
    WIDTH, which maps the SVG openings too wide (squished panel, openings landing
    off the painted hexes). The SVG silhouette IS the blue slab, so we bound the
    blue wash itself (b clearly dominant) and trim strays with percentile cuts,
    giving a stable rectangle whose aspect tracks the SVG. Returns None if too
    little blue is found (caller falls back to auto_bbox)."""
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    blue = (b > 110) & ((b - r) > 15) & ((b - g) > 0)
    ys, xs = np.where(blue)
    if len(xs) < 5000:
        return None
    L = int(np.percentile(xs, 0.3))
    R = int(np.percentile(xs, 99.7))
    T = int(np.percentile(ys, 0.1))
    B = int(np.percentile(ys, 99.9))
    if R - L < 10 or B - T < 10:
        return None
    return (L, T, R + 1, B + 1)


def lock_aspect(bbox, viewbox):
    """Snap bbox to the SVG viewBox aspect, anchored on the bbox center.

    The painted panel body is usually a hair narrower than the SVG silhouette
    (watercolor slab vs dieline). Mapping the SVG into a slightly-wrong aspect
    distorts every opening (hexes go squat/tall, the slot widens). We keep the
    bbox HEIGHT (long axis, well-defined by the slab), recompute WIDTH = height *
    (viewBox_w / viewBox_h), and re-center on the original bbox center so each
    opening lands at the correct SHAPE on the painted hexes."""
    L, T, R, B = bbox
    _, _, vw, vh = viewbox
    h = B - T
    target_w = h * (vw / vh)
    cx = (L + R) / 2.0
    return (cx - target_w / 2.0, T, cx + target_w / 2.0, B)


def mapper(viewbox, bbox):
    """Affine SVG-coord -> panel-px (identical convention to svg_geometry_check)."""
    min_x, min_y, box_w, box_h = viewbox
    L, T, R, B = bbox
    sx = (R - L) / box_w
    sy = (B - T) / box_h

    def f(x, y):
        return (L + (x - min_x) * sx, T + (y - min_y) * sy)

    return f


def poly_px(poly, f):
    return [f(x, y) for x, y in poly.exterior.coords]


def raster_mask(size_wh, polys_px) -> np.ndarray:
    """Filled boolean mask (H, W) for one or more polygons given in px coords."""
    W, H = size_wh
    m = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(m)
    for pts in polys_px:
        d.polygon([(float(x), float(y)) for x, y in pts], fill=255)
    return np.asarray(m) > 127


def sample_opening_tone(arr: np.ndarray, body_mask: np.ndarray,
                        core_white: bool = True) -> np.ndarray:
    """Pale near-white center tone, sampled from the model's OWN existing openings.

    The model already painted pale interiors inside its (drifted) hexes/slot.
    We take the brightest body pixels (its opening fills) and use their mean as
    the pale center, so the re-seated openings carry the same paper-white the
    artist used rather than a synthetic #fff.

    ``core_white`` (default True): some sources paint the hex/slot interiors as a
    pale BLUE wash (e.g. b~232 with the other channels lower). That fails the
    geometry check's white-IoU, which calls a cutout pixel "clean" only when ALL
    channels are near-white (>=240) — a pale-blue core reads as painted and tanks
    white-IoU to 0 even though placement is exact. So we raise the per-channel
    FLOOR to 242 (keeping any natural warmth above that), which makes the cutout
    cores read as clean paper-white while the navy bevel rim still sells the
    painted recess. Set False to keep the source's literal pale tint."""
    inside = arr[body_mask]
    if inside.size == 0:
        return np.array([245, 246, 248], dtype=np.float64)
    lum = inside.mean(axis=1)
    thresh = np.percentile(lum, 90)  # brightest decile = the painted openings
    bright = inside[lum >= thresh]
    tone = bright.mean(axis=0)
    if core_white:
        # near-white floor so every channel clears the white-IoU threshold; the
        # bevel rim (navy shadow / pale lip) is painted ON TOP afterward, so the
        # recess still reads as illustrated, not a flat die-punch.
        tone = np.clip(tone, 242, 252)
    else:
        # keep it pale but not pure white so the bevel has something to sit on
        tone = np.clip(tone, 232, 250)
    return tone


def sample_shadow_tone(arr: np.ndarray, body_mask: np.ndarray) -> np.ndarray:
    """Dark-navy inner-shadow color, sampled from the model's darkest body pixels
    (its own deepest blue/outline) so the bevel shadow matches the watercolor."""
    inside = arr[body_mask]
    if inside.size == 0:
        return np.array([28, 38, 78], dtype=np.float64)
    lum = inside.mean(axis=1)
    thresh = np.percentile(lum, 8)  # darkest pixels = deep shadow blue / linework
    dark = inside[lum <= thresh]
    tone = dark.mean(axis=0)
    # nudge toward navy and clamp so it never goes muddy-black
    tone = np.array([min(tone[0], 60), min(tone[1], 70), max(tone[2], 70)])
    tone = np.clip(tone, 14, 110)
    return tone


def sample_body_tone(arr: np.ndarray, body_only: np.ndarray) -> np.ndarray:
    """Mid watercolor body color (the painted panel blue), used to ERASE the
    model's own drifted openings before re-seating the exact ones. Sampled as the
    median of mid-luminance body pixels so it lands on the panel field, not the
    outline ink or the pale opening fills."""
    inside = arr[body_only]
    if inside.size == 0:
        return np.array([60, 90, 165], dtype=np.float64)
    lum = inside.mean(axis=1)
    lo, hi = np.percentile(lum, 35), np.percentile(lum, 75)
    band = inside[(lum >= lo) & (lum <= hi)]
    if band.size == 0:
        band = inside
    return np.median(band, axis=0)


def cover_local_drift(out_arr, arr, opening_mask, body_only, body_tone,
                      window_px, rng):
    """Cover ONLY the model's own drifted version of ONE opening, within a tight
    window around that opening's exact aperture. Returns the modified out_arr.

    The v1 bug: a GLOBAL scan for pale/desaturated patches treated the control
    hardware (white knobs, light slider tracks, colored dots) as "drifted
    openings" and smeared them into body color. Fix: the drift of an opening is
    always LOCAL — the model painted the same opening, just shifted by a small
    offset, so its bright fill + dark rim sit within ~`window_px` of the exact
    aperture. We restrict every destructive test to that window, so any control
    further away is never a candidate and survives verbatim.

    Within the window, the model's drifted opening reads as the brightest, least-
    saturated patch (its pale fill) plus the dark ring hugging it. We cover both
    with procedural body-toned watercolor so nothing ghosts behind the re-seated
    exact opening. The exact aperture itself is excluded — it's repainted by the
    bevel step, which must own those pixels.

    The white-spill case (RESEAT-np02ft-v2): when the SOURCE painted an opening as
    a large WHITE/pale blob that is OVERSIZED or OFFSET vs the exact aperture, the
    white that spills just OUTSIDE the exact aperture survives — on a LIGHT body the
    relative "pale = lighter than body" test under-fires (the spill isn't 24 lum
    above a pale body), so a white ring is left painted at the wrong place and tanks
    white-IoU (the geometry check counts it as opening-white off-coordinate). We add
    an ABSOLUTE near-white cover: any near-white pixel (high lum, low sat) inside the
    window and outside the exact aperture is body-toned too. The window guard keeps
    it clear of the controls (no control sits within the tight window); ~opening_mask
    keeps it off the aperture interior, which the bevel step owns.
    """
    H, W, _ = arr.shape
    lum = arr.mean(axis=2)
    sat = arr.max(axis=2) - arr.min(axis=2)
    body_lum = float(body_tone.mean())
    body_sat = float(body_tone.max() - body_tone.min())

    # LOCAL window: a dilation of the exact aperture. Drift is small relative to
    # the panel, so the model's version of this opening lives inside here.
    dist_out = distance_transform_edt(~opening_mask)
    window = dist_out <= window_px

    # Candidate area: INSIDE the window and in the body (never the exact aperture,
    # never outside the contour). Everything destructive below is masked to this so
    # a control further out than the window can never be a candidate.
    in_win = window & body_only & ~opening_mask
    if not in_win.any():
        return out_arr

    # (A) RELATIVE drift: the model's drifted opening = a bright pale FILL plus the
    # dark painted RIM hugging it, read RELATIVE to the body wash. Both must go, or
    # the dark rim ghosts as a halo around the re-seated opening.
    pale = (lum >= (body_lum + 24)) & (sat <= (body_sat * 0.75 + 16))
    seed = in_win & pale
    drift_mask = np.zeros((H, W), bool)
    if seed.any():
        # Grow the pale-fill seed generously to swallow the dark bevel RING that
        # hugs it (the source's own painted opening rim — the v2-pre halo culprit).
        # Stay inside the window so we can't reach a control. Within this grown
        # footprint we cover every pixel that deviates from the body wash in EITHER
        # direction (bright fill OR dark rim); body-toned pixels are left alone.
        grow = max(10.0, window_px * 0.55)
        d_seed = distance_transform_edt(~seed)
        near_seed = d_seed <= grow
        deviates = np.abs(lum - body_lum) >= 18  # not already body-toned
        drift_mask = in_win & near_seed & (deviates | (d_seed <= 3))

    # (B) ABSOLUTE near-white spill: the oversized/offset white aperture fill that
    # the relative test misses on a light body. Thresholds are absolute (not body-
    # relative) so they catch the model's white regardless of how pale the body is.
    # The geometry check calls a pixel "opening-white" when ALL channels >= 240
    # (lum >= 240, sat ~0); a slightly looser band here covers those plus their pale
    # fringe so no white sliver is left to inflate the white-IoU union.
    near_white = in_win & (lum >= 236.0) & (sat <= 30.0)

    patch_mask = drift_mask | near_white
    if not patch_mask.any():
        return out_arr

    # Procedural watercolor MOTTLE (independent of the original pixels, so neither
    # the old bright fill nor its dark bevel can re-imprint as a ghost): three
    # octaves of body-toned noise — broad blotches, mid mottle, fine paper grain —
    # so the repaint matches the surrounding wash instead of reading as flat putty.
    def oct(sig, amp):
        n = gaussian_filter(rng.normal(0, 1, (H, W)), sigma=sig)
        return n / (np.abs(n).max() + 1e-6) * amp
    mottle = oct(9, 13) + oct(3.0, 8) + oct(1.0, 5)
    patch = np.clip(body_tone[None, None, :] + mottle[..., None], 0, 255)
    a = patch_mask.astype(np.float64)
    a = np.minimum(a, gaussian_filter(a, sigma=1.8) * 1.8)
    a = np.clip(a, 0, 1)[..., None]
    return out_arr * (1 - a) + patch * a


def build_bevel(opening_mask: np.ndarray, ll_center, art_shape, rng,
                tone_center, tone_shadow, ring_px: float, rim_scale: float = 1.0):
    """Return (rgb_layer, alpha) painting one opening: pale interior + illustrated rim.

    The rim is a distance-feathered ring inside the exact edge. Its strength is
    split by edge orientation — upper-left arc gets the dark inner shadow, the
    lower-right arc gets a pale lit lip — and the ring width is jittered with
    low-frequency noise so it looks brushed, not stroked by a vector pen.

    ``rim_scale`` (>=1.0) makes the rim BOLDER: it widens the painted band and
    deepens the shadow/lip opacity so the bevel reads like the references'
    hand-painted recess rather than a faint code line. The clean white core is
    still protected by the inradius cap, so geometry/white-IoU stay high.
    """
    H, W = opening_mask.shape
    # distance (px) from each interior pixel to the nearest opening edge
    dist_in = distance_transform_edt(opening_mask)
    # Boldness is DECOUPLED from width: rim_scale deepens the shadow/lip OPACITY
    # (below), it does NOT widen the band. The band stays THIN and edge-hugging so
    # a big clean white core survives and white-on-coordinate IoU stays high. We
    # only widen the band a little (sqrt) with rim_scale so a bolder rim reads
    # without eating the core.
    ring_px = ring_px * (1.0 + 0.30 * (rim_scale - 1.0))
    # cap the rim on NARROW openings (e.g. the long thin slot): the inradius is
    # max(dist_in); keep the rim under ~26% of it so a clean white core always
    # survives and the white-on-coordinate IoU stays high for thin shapes.
    inradius = float(dist_in.max())
    ring_px = min(ring_px, max(2.5, inradius * 0.26))

    # angle of each pixel relative to the opening centroid -> which arc it faces.
    ys, xs = np.nonzero(opening_mask)
    cy, cx = ll_center
    Y, X = np.mgrid[0:H, 0:W]
    # light comes from lower-right; shadow on upper-left.
    # ul weight high toward up-left (-x,-y), lr weight high toward down-right.
    ang = np.arctan2((Y - cy), (X - cx))  # radians, 0 = +x(right), pi/2 = +y(down)
    # upper-left direction ~ angle 5pi/4 (down-left is +,+ ... be explicit):
    # up-left vector = (-1,-1) -> atan2(-1,-1) = -3pi/4. lower-right = (1,1) -> pi/4.
    ul_dir = -3 * np.pi / 4
    lr_dir = np.pi / 4

    def lobe(a, d):
        # cosine lobe centered on direction d, in [0,1]
        return np.clip(np.cos(a - d), 0, 1)

    ul_w = lobe(ang, ul_dir)
    lr_w = lobe(ang, lr_dir)

    # low-frequency irregularity so the ring width breathes around the rim
    # (two octaves: a broad wobble + a finer brush jitter -> hand-painted edge).
    n1 = gaussian_filter(rng.standard_normal((H, W)), sigma=max(3.0, ring_px * 0.9))
    n2 = gaussian_filter(rng.standard_normal((H, W)), sigma=max(1.2, ring_px * 0.3))
    noise = n1 / (np.abs(n1).max() + 1e-6) + 0.5 * n2 / (np.abs(n2).max() + 1e-6)
    noise = noise / (np.abs(noise).max() + 1e-6)
    ring_local = ring_px * (1.0 + 0.5 * noise)
    ring_local = np.clip(ring_local, ring_px * 0.4, ring_px * 1.8)

    # ring falloff: 1 at the edge (dist 0) -> 0 at dist=ring_local. A high
    # exponent keeps the painted rim hugging the EDGE and leaves a big clean
    # white center (so the geometry check reads white exactly on coordinate and
    # painted-fraction stays low in the central area). Bolder rim => slightly
    # sharper falloff so the dark sits crisply on the edge instead of bleeding in.
    falloff_exp = 2.4 + 0.6 * (rim_scale - 1.0)
    t = np.clip(dist_in / np.maximum(ring_local, 1e-3), 0, 1)
    ring = np.where(opening_mask, (1.0 - t) ** falloff_exp, 0.0)

    rgb = np.zeros((H, W, 3), dtype=np.float64)
    alpha = np.zeros((H, W), dtype=np.float64)

    # 1) pale interior fill everywhere inside the opening
    interior_a = opening_mask.astype(np.float64)
    rgb += tone_center[None, None, :] * interior_a[..., None]
    alpha = np.maximum(alpha, interior_a)

    # 2) dark inner shadow on the upper-left arc — the dominant bevel cue in the
    # references. Deepen it (and let the dark wrap a bit past the up-left lobe so
    # the whole rim carries a navy edge, not just a sliver) so the recess reads
    # boldly painted. Opacity climbs toward full at rim_scale>=1.4.
    shadow_strength = min(1.0, 0.95 * rim_scale)
    sa = np.clip(ring * (0.35 + 0.65 * ul_w) * shadow_strength, 0, 1)
    rgb = rgb * (1 - sa[..., None]) + tone_shadow[None, None, :] * sa[..., None]
    alpha = np.maximum(alpha, sa)

    # 3) pale lit lip on the lower-right arc (brighter than center) — the catch-
    # light that sells the bevel. Boldened with rim_scale too.
    lip_tone = np.clip(tone_center + 12, 0, 255)
    la = np.clip(ring * lr_w * min(1.0, 0.75 * rim_scale), 0, 1)
    rgb = rgb * (1 - la[..., None]) + lip_tone[None, None, :] * la[..., None]

    # 4) gaussian feather so no hard vector edge survives (watercolor softness)
    feather = max(0.8, ring_px * 0.18)
    for c in range(3):
        rgb[..., c] = gaussian_filter(rgb[..., c], sigma=feather)
    alpha = gaussian_filter(alpha, sigma=feather)
    # re-confine alpha to (exact opening dilated by ~1 feather) so the rim sits
    # ON the edge and coverage never leaks far past the exact opening.
    confine = distance_transform_edt(~opening_mask) <= (feather * 1.5)
    alpha = np.where(confine, alpha, 0.0)
    alpha = np.clip(alpha, 0, 1)
    return rgb, alpha


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--art", required=True, type=Path, help="model-generated panel PNG")
    ap.add_argument("--svg", required=True, type=Path, help="authoritative SVG template")
    ap.add_argument("--bbox", help="L,T,R,B panel region in art px (default: per --bbox-mode)")
    ap.add_argument("--bbox-mode", choices=["auto", "blue", "blue-locked"], default="blue-locked",
                    help="how to auto-detect the panel bbox when --bbox is omitted. "
                         "auto=non-white bounds (legacy; over-wide when knobs/ticks "
                         "overhang the slab). blue=bound the blue wash only (ignores "
                         "overhanging hardware). blue-locked=blue bounds then snap to "
                         "the SVG aspect so openings keep their exact shape (default).")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--debug-overlay", type=Path, help="also write an exact-edge overlay PNG")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--rim-scale", type=float, default=1.4,
                    help="bevel boldness (>=1.0). 1.0=subtle v1 rim, 1.4=bold (default)")
    ap.add_argument("--no-local-erase", action="store_true",
                    help="skip covering the model's drifted opening (debug: see raw drift ghosts)")
    ap.add_argument("--core-tint", action="store_true",
                    help="keep the source's literal pale tint inside cutouts (may be "
                         "pale-blue and fail white-IoU). Default raises the core to "
                         "near-white so cutouts read clean.")
    args = ap.parse_args()

    art_path = args.art if args.art.is_absolute() else ROOT / args.art
    svg = args.svg if args.svg.is_absolute() else ROOT / args.svg
    out = args.out if args.out.is_absolute() else ROOT / args.out

    img = Image.open(art_path).convert("RGB")
    W, H = img.size
    arr = np.asarray(img).astype(np.float64)

    rng = np.random.default_rng(args.seed)

    viewbox, shapes = C.extract_shapes(svg)
    shapes = C.classify(shapes)

    arr_u8 = np.asarray(img)
    if args.bbox:
        bbox = tuple(float(v) for v in args.bbox.split(","))
        bbox_src = "explicit"
    elif args.bbox_mode == "auto":
        bbox = auto_bbox(arr_u8)
        bbox_src = "auto(non-white)"
    else:
        bb = blue_body_bbox(arr_u8)
        if bb is None:
            bbox = auto_bbox(arr_u8)
            bbox_src = "blue->auto-fallback"
        elif args.bbox_mode == "blue-locked":
            bbox = lock_aspect(bb, viewbox)
            bbox_src = "blue-locked"
        else:
            bbox = bb
            bbox_src = "blue"

    body = [s for s in shapes if s.polygon is not None and s.role in ("outer_contour", "paintable_region")]
    cuts = [s for s in shapes if s.polygon is not None and s.role == "internal_cutout"]

    # Register by the OUTER CONTOUR, not the raw viewBox. --bbox is the painted
    # panel (auto_bbox = non-white bounds = the contour as drawn); the viewBox
    # usually carries a margin the contour doesn't fill, so mapping the full viewBox
    # onto the panel bbox shifts+scales every opening a few px off-coordinate. BOTH
    # graders (svg_geometry_check, geom_iou) register by contour bounds — so the
    # compositor must too, or the bevel paints each aperture off where they measure
    # it, and that misplaced bevel-white reads as "white just outside the opening"
    # and tanks white-IoU. Fall back to the viewBox only when there is no contour.
    if body:
        cx0 = min(s.bounds[0] for s in body); cy0 = min(s.bounds[1] for s in body)
        cx1 = max(s.bounds[2] for s in body); cy1 = max(s.bounds[3] for s in body)
        src = (cx0, cy0, cx1 - cx0, cy1 - cy0)
    else:
        src = viewbox
    f = mapper(src, bbox)

    contour_mask = raster_mask((W, H), [poly_px(s.polygon, f) for s in body])

    # 1) clear outside-contour to white (exact silhouette)
    out_arr = arr.copy()
    out_arr[~contour_mask] = [255.0, 255.0, 255.0]

    # color sampling from the model's own painting (body minus the exact openings)
    openings_mask = raster_mask((W, H), [poly_px(s.polygon, f) for s in cuts]) if cuts else np.zeros((H, W), bool)
    body_only = contour_mask & ~openings_mask
    tone_center = sample_opening_tone(arr, contour_mask & openings_mask if openings_mask.any() else contour_mask,
                                      core_white=not args.core_tint)
    tone_shadow = sample_shadow_tone(arr, body_only)
    body_tone = sample_body_tone(arr, body_only)

    # ring width scales with the panel size so it reads the same on any resolution
    panel_h = bbox[3] - bbox[1]
    ring_px = max(2.5, panel_h * 0.0052)  # ~0.52% of panel height — thin base rim
    # local-drift window: how far from the exact aperture we look for the model's
    # OWN drifted version of this opening. Scaled to the panel so it tracks the
    # observed drift magnitude (a few % of panel height) without ever reaching a
    # control. Capped so a small opening can't sweep half the body.
    window_px = max(18.0, panel_h * 0.030)

    # NOTE (v2): we do NOT globally scan/erase the body for "drifted" pale
    # patches — that erased the controls in v1. All destructive work below is
    # confined to a window around each exact opening.
    for s in cuts:
        pts = poly_px(s.polygon, f)
        m = raster_mask((W, H), [pts])
        if not m.any():
            continue
        # per-opening seed variation so each rim/cover is a little different
        oseed = np.random.default_rng(int(rng.integers(0, 1_000_000)))
        # 1) cover ONLY this opening's drifted twin, in a tight local window
        if not args.no_local_erase:
            # cap the window to ~80% of the opening's own inradius beyond its edge
            # so it never balloons past the local neighborhood on big openings.
            local_win = min(window_px, max(18.0, float(distance_transform_edt(m).max()) * 1.6))
            out_arr = cover_local_drift(out_arr, arr, m, body_only, body_tone,
                                        local_win, oseed)
        # 2) paint the exact opening: pale clear + bold bevel rim
        ys, xs = np.nonzero(m)
        ll_center = (ys.mean(), xs.mean())
        rgb_layer, alpha = build_bevel(m, ll_center, arr.shape, oseed,
                                       tone_center, tone_shadow, ring_px,
                                       rim_scale=args.rim_scale)
        a3 = alpha[..., None]
        out_arr = out_arr * (1 - a3) + rgb_layer * a3

    out_img = Image.fromarray(np.clip(out_arr, 0, 255).astype(np.uint8))
    out.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(out)

    # self-check: painted fraction in the CLEAN central core (opening eroded so
    # the bevel ring is excluded) — the prompt wants this near zero.
    final = np.asarray(out_img)
    painted = np.any(final < 240, axis=2)
    cores = []
    for s in cuts:
        m = raster_mask((W, H), [poly_px(s.polygon, f)])
        if not m.any():
            continue
        d = distance_transform_edt(m)
        core = d >= (0.45 * d.max())  # inner ~core, bevel ring excluded
        if core.any():
            cores.append(float(np.sum(painted & core) / np.sum(core)))
    print(f"out -> {rel(out)}")
    if cores:
        print(f"core painted-frac (bevel excluded): mean={np.mean(cores):.4f} max={max(cores):.4f}")
    bbox_str = ",".join(str(int(round(v))) for v in bbox)
    print(
        "MEASURE WITH (use this exact bbox — it's where the geometry was placed):\n"
        f"  python3 scripts/svg_geometry_check.py {rel(out)} "
        f"--svg {rel(svg)} --bbox {bbox_str}"
    )
    print(f"bbox: {tuple(round(v,1) for v in bbox)}  ({bbox_src})   ring_px: {ring_px:.1f}   "
          f"rim_scale: {args.rim_scale}   window_px: {window_px:.1f}   "
          f"local_erase: {not args.no_local_erase}")
    print(f"tone_center: {tone_center.round(1).tolist()}   tone_shadow: {tone_shadow.round(1).tolist()}")
    print(f"body_tone: {np.asarray(body_tone).round(1).tolist()}")

    if args.debug_overlay:
        ov = out_img.copy()
        d = ImageDraw.Draw(ov, "RGBA")
        for s in body:
            p = poly_px(s.polygon, f)
            d.line(p + [p[0]], fill=(0, 230, 0, 255), width=3)
        for s in cuts:
            p = poly_px(s.polygon, f)
            d.line(p + [p[0]], fill=(235, 40, 40, 255), width=2)
        op = args.debug_overlay if args.debug_overlay.is_absolute() else ROOT / args.debug_overlay
        op.parent.mkdir(parents=True, exist_ok=True)
        ov.save(op)
        print(f"debug-overlay -> {rel(op)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
