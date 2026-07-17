#!/usr/bin/env python3
"""Aggressive green-spill purge for chroma-keyed RGBA art (R23).

Runs AFTER chroma_key + decontam_binarize. Exploits the dark-outline leeway:
the outer contour is ink-dark, so eroding/repainting 1-2 px at the edge costs
nothing visually and removes the stray green pixels that survive keying.

Passes:
  1. edge-band green suppression — inside a band N px in from the alpha edge,
     any green-dominant pixel is repainted from its nearest non-green neighbor
  2. optional 1 px alpha erode of the outer silhouette
  3. global near-key kill — pixels within deltaE00 < tau of the key color, in
     components <= max-comp px (protects legitimate large green art elements),
     repainted from local median
  4. verify loop — exact D3b criterion (deltaE00 < 6, fg alpha>0.5) must be 0
"""
from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("This script requires /usr/bin/python3 (PATH python3 lacks numpy/PIL). Re-run with /usr/bin/python3.", file=sys.stderr)
    sys.exit(2)

from scipy import ndimage as ndi
from skimage.color import deltaE_ciede2000, rgb2lab

DONOR_ALPHA_THRESH = 127
DONOR_DOMINANCE_MAX = 18
DONOR_KEY_DE_MIN = 10.0
DONOR_SEARCH_RADIUS = 60
# convergence-loop caps (constants, not CLI flags, so tests can shrink them
# deterministically to exercise the fail-closed non-convergence path without
# changing default behavior on the validated pipeline)
VERIFY_MAX_ITERATIONS = 8
FINAL_SWEEP_MAX_ITERATIONS = 10


def hex_rgb(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))


def repaint(
    img: np.ndarray,
    bad: np.ndarray,
    key_lab: np.ndarray | None = None,
    search_radius: int = DONOR_SEARCH_RADIUS,
) -> int:
    """Replace bad px RGB with the nearest SAFE donor pixel's RGB.

    A safe donor is: opaque (alpha >= DONOR_ALPHA_THRESH), not green-dominant
    (g - max(r,b) <= DONOR_DOMINANCE_MAX), and (if key_lab given) not near the
    key color (deltaE00 >= DONOR_KEY_DE_MIN). This prevents a bad pixel from
    donor-copying a transparent/key-green neighbor's RGB into opaque
    foreground (the round-7 audit's synthetic repro).

    Bad pixels are NEVER eligible as their own (or each other's) donor, even
    when they otherwise satisfy the safe-donor predicates above -- a bad
    pixel that happens to be opaque/non-dominant/non-key-adjacent would
    otherwise have distance 0 to itself and "donate" its own unchanged RGB
    to itself, leaving it untouched while being counted as filled (the
    self-donation hole; reproduced at non-default --dominance/--tau values
    where a bad pixel can slip under the safe-donor thresholds).

    Bad pixels with no safe donor within search_radius are left unchanged
    (their RGB is never invented) and counted in the returned unfilled total.
    """
    if not bad.any():
        return 0
    alpha = img[..., 3]
    rgb = img[..., :3].astype(np.int16)
    dominance = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
    safe = (alpha >= DONOR_ALPHA_THRESH) & (dominance <= DONOR_DOMINANCE_MAX) & ~bad
    if key_lab is not None:
        lab = rgb2lab(img[..., :3].astype(np.float32) / 255.0)
        de = deltaE_ciede2000(lab, key_lab)
        safe &= de >= DONOR_KEY_DE_MIN
    if not safe.any():
        return int(bad.sum())
    unsafe = ~safe
    dist, (iy, ix) = ndi.distance_transform_edt(
        unsafe, return_distances=True, return_indices=True
    )
    fillable = bad & (dist <= search_radius)
    img[..., :3][fillable] = img[..., :3][iy[fillable], ix[fillable]]
    return int((bad & ~fillable).sum())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rgba")
    ap.add_argument("out")
    ap.add_argument("--key", default="#00FF00")
    ap.add_argument("--band", type=int, default=4, help="edge band px for green suppression")
    ap.add_argument("--dominance", type=int, default=18, help="g - max(r,b) threshold in band")
    ap.add_argument("--erode", type=int, default=1, help="outer alpha erode px")
    ap.add_argument("--tau", type=float, default=10.0, help="global near-key deltaE00 kill")
    ap.add_argument("--max-comp", type=int, default=200, help="component cap for global kill")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument(
        "--no-green-art",
        action="store_true",
        help="the prompt guaranteed no bright pure-green art: remove ALL "
        "key-hue green unconditionally (no shape-based protection)",
    )
    args = ap.parse_args()

    if os.path.abspath(args.rgba) == os.path.abspath(args.out):
        err = {"error": "in_place_operation_rejected", "rgba": args.rgba, "out": args.out}
        print(json.dumps(err))
        if args.json_out:
            with open(args.json_out, "w") as fh:
                json.dump(err, fh, indent=2)
        return 2

    key_rgb = hex_rgb(args.key)
    key_lab = rgb2lab((np.array(key_rgb, dtype=np.float32).reshape(1, 1, 3) / 255.0))
    img = np.asarray(Image.open(args.rgba).convert("RGBA")).copy()
    stats: dict = {}

    # 2. erode outer silhouette first so band ops act on final edge
    if args.erode > 0:
        fg = img[..., 3] > 127
        er = ndi.binary_erosion(fg, iterations=args.erode, border_value=0)
        removed = fg & ~er
        img[..., 3][removed] = 0
        stats["eroded_px"] = int(removed.sum())

    # 1. edge-band green suppression
    fg = img[..., 3] > 127
    inner = ndi.binary_erosion(fg, iterations=args.band, border_value=0)
    band = fg & ~inner
    rgb = img[..., :3].astype(np.int16)
    dominance = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
    band_green = band & (dominance > args.dominance)
    stats["band_green_px"] = int(band_green.sum())
    stats["band_green_unfilled_px"] = repaint(img, band_green, key_lab)

    # with no green art guaranteed, no edge pixel may lean green AT ALL:
    # clamp g <= max(r,b) across the whole edge band (kills the dark olive
    # fringe at junction notches that survives every threshold pass)
    if args.no_green_art:
        rgb = img[..., :3].astype(np.int16)
        g = rgb[..., 1]
        other = np.maximum(rgb[..., 0], rgb[..., 2])
        # edge band: no green lean at all; interior: cap the lean at +8 so
        # neutral washes keep their grain but nothing reads green anywhere
        cap = np.where(band, other, other + 8)
        tinge = (img[..., 3] > 0) & (g > cap)
        stats["band_declamp_px"] = int((tinge & band).sum())
        stats["global_declamp_px"] = int((tinge & ~band).sum())
        rgb[..., 1] = np.minimum(g, np.where(img[..., 3] > 0, cap, g))
        img[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)

        # dark-olive notch kill: deep concave junctions hold dark key blends
        # that read khaki (g ~ r, low blue) — legit dark ink is warm (r > g).
        # repaint them from neighboring art
        rgb = img[..., :3].astype(np.int16)
        r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        olive = (
            band
            & (g_ > b_ + 20)
            & (g_ > r_ - 12)
            & (g_ < 140)
            & (img[..., 3] > 0)
        )
        # geometry restriction: only inside concave notches (regions the
        # background swallows under morphological closing), and never near a
        # thick olive mass (sage seaweed edges are legitimately this color)
        fgm = img[..., 3] > 127
        notch = ndi.binary_closing(~fgm, structure=np.ones((9, 9), bool)) & fgm
        olive_mass = (img[..., 3] > 0) & (g_ > b_ + 20) & (g_ > r_ - 12)
        inscribed = ndi.distance_transform_edt(olive_mass)
        thick_olive = inscribed >= 6
        near_seaweed = ndi.distance_transform_edt(~thick_olive) <= 12
        olive &= notch & ~near_seaweed
        stats["olive_notch_px"] = int(olive.sum())
        stats["olive_notch_unfilled_px"] = repaint(img, olive, key_lab)

        # near-black khaki neutralize: notch shadows like (44,44,3) read dark
        # olive; raising blue toward green at this darkness is invisible but
        # kills the green cast. Pure color-space fix, band-wide, no repaint.
        rgb = img[..., :3].astype(np.int16)
        r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
        dark_khaki = (
            band
            & (img[..., 3] > 0)
            & (np.maximum(r_, g_) < 95)
            & (g_ > b_ + 15)
            & (g_ >= r_ - 12)
        )
        stats["dark_khaki_px"] = int(dark_khaki.sum())
        rgb[..., 2] = np.where(dark_khaki, np.maximum(b_, g_ - 8), b_)
        rgb[..., 1] = np.where(dark_khaki, np.minimum(g_, r_ + 4), rgb[..., 1])
        img[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)

    # 3. global near-key kill, small components only
    lab = rgb2lab(img[..., :3].astype(np.float32) / 255.0)
    de = deltaE_ciede2000(lab, key_lab)
    near = (img[..., 3] > 0) & (de < args.tau)
    lbl, n = ndi.label(near, structure=np.ones((3, 3), bool))
    if n:
        sizes = ndi.sum(near, lbl, range(1, n + 1))
        kill = np.isin(lbl, [i + 1 for i, s in enumerate(sizes) if s <= args.max_comp])
        stats["global_kill_px"] = int(kill.sum())
        stats["protected_components"] = int((sizes > args.max_comp).sum())
        stats["global_kill_unfilled_px"] = repaint(img, kill, key_lab)
    else:
        stats["global_kill_px"] = 0
        stats["protected_components"] = 0

    # 3b. strong-green speck kill — tiny isolated bright-green components
    # anywhere in the art are baked-in key contamination (the model painted
    # on green), not legit art; large components (seaweed etc.) are protected
    rgb = img[..., :3].astype(np.int16)
    dom = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
    strong = (img[..., 3] > 0) & (dom > 45) & (rgb[..., 1] > 150)
    # legit green art = broad-green connected mass > 500 px (seaweed etc.);
    # strong-green pixels are protected only within (a small dilation of)
    # such a mass — everything else is baked-in key contamination
    broad = (img[..., 3] > 0) & (dom > 25) & (rgb[..., 1] > 120)
    lbl, n = ndi.label(broad, structure=np.ones((3, 3), bool))
    if n:
        sizes = ndi.sum(broad, lbl, range(1, n + 1))
        legit = np.isin(lbl, [i + 1 for i, s in enumerate(sizes) if s > 500])
        legit = ndi.binary_dilation(legit, iterations=3)
    else:
        legit = np.zeros(strong.shape, bool)
    speck = strong & ~legit
    stats["speck_kill_px"] = int(speck.sum())
    stats["speck_protected_px"] = int((strong & legit).sum())
    stats["speck_kill_unfilled_px"] = repaint(img, speck, key_lab)

    # 4. verify loop on exact D3b criterion, with margin. Repainting from
    # neighbors copies adjacent greens and can loop forever on legit bright-
    # green art (seaweed highlights), so instead dull the pixel itself:
    # reduce green dominance until it leaves the key neighborhood.
    for it in range(VERIFY_MAX_ITERATIONS):
        lab = rgb2lab(img[..., :3].astype(np.float32) / 255.0)
        de = deltaE_ciede2000(lab, key_lab)
        bad = (img[..., 3].astype(np.float32) / 255.0 > 0.5) & (de < 7.0)
        if not bad.any():
            stats["verify_iterations"] = it
            break
        rgb = img[..., :3].astype(np.int16)
        g = rgb[..., 1]
        rgb[..., 1] = np.where(bad, np.maximum(g - 25, np.maximum(rgb[..., 0], rgb[..., 2])), g)
        rgb[..., 0] = np.where(bad, np.minimum(rgb[..., 0] + 12, 255), rgb[..., 0])
        img[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    else:
        stats["verify_iterations"] = -1  # did not converge

    # 4b. trapped-background removal — darkened key-color blends survive
    # between thin strands (fans, filaments) with full alpha. Key-HUE green
    # (r ~ b, strong green dominance, not dark) is background showing
    # through, never watercolor art: legit greens are olive/warm (r >> b).
    # These pixels become transparent, not repainted.
    rgb = img[..., :3].astype(np.int16)
    dom = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
    keyhue = (
        (img[..., 3] > 0)
        & (dom > 25)
        & (np.abs(rgb[..., 0] - rgb[..., 2]) < 45)
        & (rgb[..., 1] > 45)
    )
    # color alone cannot separate pure-green ART (seaweed can be [1,137,0])
    # from trapped key background — but SHAPE can: leaves are solid compact
    # blobs, trapped background is a stringy lattice between filaments.
    # Protect keyhue components that are large AND compact (bbox fill ratio).
    lbl, n = ndi.label(keyhue, structure=np.ones((3, 3), bool))
    trapped = np.zeros_like(keyhue)
    solid = np.zeros_like(keyhue)
    if args.no_green_art:
        trapped = keyhue.copy()
        n = 0
    if n:
        # solidity via max inscribed radius: leaves/blobs are thick (>=7 px
        # radius somewhere), trapped lattice strips between filaments are thin
        thick_r = ndi.distance_transform_edt(keyhue)
        slices = ndi.find_objects(lbl)
        for i, sl in enumerate(slices):
            comp = lbl[sl] == i + 1
            area = int(comp.sum())
            max_r = float(thick_r[sl][comp].max())
            if area >= 300 and max_r >= 7.0:
                solid[sl] |= comp  # thick blob = legit art
            else:
                trapped[sl] |= comp
        # small compact green near a solid mass is art detail (berries,
        # leaf tips), not a trapped pocket — pockets sit among filaments
        near_solid = ndi.distance_transform_edt(~solid) <= 15
        keep = trapped & near_solid
        trapped &= ~near_solid
        stats["trapped_kept_near_art_px"] = int(keep.sum())
    stats["trapped_bg_px"] = int(trapped.sum())
    stats["trapped_protected_px"] = int(solid.sum())
    img[..., 3][trapped] = 0

    # 5. final sweep — repaint passes copy colors and can themselves deposit
    # green; dull (never copy) any remaining strong-green outside the legit
    # mass until none is left
    sweep_dom = 30 if args.no_green_art else 45
    sweep_g = 110 if args.no_green_art else 150
    for it in range(FINAL_SWEEP_MAX_ITERATIONS):
        rgb = img[..., :3].astype(np.int16)
        dom = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
        resid = (img[..., 3] > 0) & (dom > sweep_dom) & (rgb[..., 1] > sweep_g)
        if not args.no_green_art:
            resid &= ~legit
        if not resid.any():
            stats["final_sweep_iterations"] = it
            break
        g = rgb[..., 1]
        rgb[..., 1] = np.where(resid, np.maximum(g - 30, np.maximum(rgb[..., 0], rgb[..., 2]) + 30), g)
        img[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    stats["final_sweep_px"] = int(resid.sum()) if "final_sweep_iterations" not in stats else 0

    # fail-closed final verdict: success requires every terminal criterion to
    # hold, not just the pass-4 verify loop. Re-measure the exact D3b
    # criterion (deltaE00 < 6, fg alpha > 0.5) on the final pixels — this is
    # what actually ships, independent of any single pass's internal state.
    lab = rgb2lab(img[..., :3].astype(np.float32) / 255.0)
    de = deltaE_ciede2000(lab, key_lab)
    residual_strong_key = (img[..., 3].astype(np.float32) / 255.0 > 0.5) & (de < 6.0)
    stats["residual_strong_key_px"] = int(residual_strong_key.sum())
    stats["verify_converged"] = stats.get("verify_iterations", -1) >= 0
    stats["final_sweep_converged"] = "final_sweep_iterations" in stats

    # every repaint() call above returns an "unfilled" count for bad pixels
    # that had no safe donor within radius -- these are NOT fixed, they were
    # only ever recorded. "Fail-closed" must mean exactly that: any of them
    # remaining nonzero blocks convergence, not just the separate residual
    # D3b re-measurement below.
    unfilled_keys = (
        "band_green_unfilled_px",
        "olive_notch_unfilled_px",
        "global_kill_unfilled_px",
        "speck_kill_unfilled_px",
    )
    total_unfilled = sum(stats.get(k, 0) for k in unfilled_keys)
    stats["total_unfilled_px"] = total_unfilled

    stats["converged"] = bool(
        stats["verify_converged"]
        and stats["final_sweep_converged"]
        and stats["residual_strong_key_px"] == 0
        and total_unfilled == 0
    )

    Image.fromarray(img).save(args.out)
    print(json.dumps(stats))
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(stats, fh, indent=2)
    return 0 if stats["converged"] else 2


if __name__ == "__main__":
    sys.exit(main())
