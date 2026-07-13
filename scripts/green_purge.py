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
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import deltaE_ciede2000, rgb2lab


def hex_rgb(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i : i + 2], 16) for i in (0, 2, 4))


def repaint(img: np.ndarray, bad: np.ndarray) -> None:
    """Replace bad px RGB with nearest non-bad pixel's RGB."""
    if not bad.any():
        return
    _, (iy, ix) = ndi.distance_transform_edt(bad, return_indices=True)
    img[..., :3][bad] = img[..., :3][iy[bad], ix[bad]]


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
    args = ap.parse_args()

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
    repaint(img, band_green)

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
        repaint(img, kill)
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
    repaint(img, speck)

    # 4. verify loop on exact D3b criterion, with margin. Repainting from
    # neighbors copies adjacent greens and can loop forever on legit bright-
    # green art (seaweed highlights), so instead dull the pixel itself:
    # reduce green dominance until it leaves the key neighborhood.
    for it in range(8):
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
    for it in range(10):
        rgb = img[..., :3].astype(np.int16)
        dom = rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2])
        resid = (img[..., 3] > 0) & (dom > 45) & (rgb[..., 1] > 150) & ~legit
        if not resid.any():
            stats["final_sweep_iterations"] = it
            break
        g = rgb[..., 1]
        rgb[..., 1] = np.where(resid, np.maximum(g - 30, np.maximum(rgb[..., 0], rgb[..., 2]) + 30), g)
        img[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    stats["final_sweep_px"] = int(resid.sum()) if "final_sweep_iterations" not in stats else 0

    Image.fromarray(img).save(args.out)
    stats["converged"] = stats.get("verify_iterations", -1) >= 0
    print(json.dumps(stats))
    if args.json_out:
        with open(args.json_out, "w") as fh:
            json.dump(stats, fh, indent=2)
    return 0 if stats["converged"] else 2


if __name__ == "__main__":
    sys.exit(main())
