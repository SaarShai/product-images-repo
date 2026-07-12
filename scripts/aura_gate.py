#!/usr/bin/env python3
"""aura_gate.py — detect the painted-glow/"aura" defect in RGBA transparent
product renders.

Some native-transparent image-gen models (OpenAI images/edits,
chatgpt-image-latest, gpt-image-1.5, ...) paint a wide soft glow/halo band
around the subject as FULLY OPAQUE pixels: the alpha channel is ~binary
(near-0 outside, near-255 inside) so it looks like a clean cutout, but a big
chunk of the "inside" is really a smooth, low-RGB-gradient color wash — the
true hand-painted/inked edge of the subject sits much further in. Real
crisp art has an ink outline or texture change right at (or within a couple
of px of) the alpha boundary; the aura defect does not.

Metric: for every pixel on the outer alpha-boundary of the subject, walk
inward (away from the background, along the direction to that pixel's own
nearest background pixel) up to --max-dist px and find the first pixel with
a strong local RGB (Sobel) gradient. That distance is the pixel's
"band_width". A boundary pixel is flagged "aura" if band_width > --near-px
(no strong edge found close to the boundary).

  aura_index       = fraction of boundary pixels flagged as aura
  mean_band_width  = mean band_width (capped at --max-dist) over all
                     boundary pixels

A debug overlay PNG is written showing: boundary pixels colored green (not
aura, edge found within --near-px) or red (aura, no strong edge found in
--near-px), and the actual detected glow band (boundary -> first strong
gradient) shaded translucent magenta for every flagged pixel.

Reference / white-background art (no real alpha channel) can be scored the
same way: alpha is synthesized as "non-white" foreground. This is detected
automatically (an image whose alpha channel is ~fully opaque, i.e. no real
transparency, is treated as a white-bg image) or forced with --nonwhite.

Usage:
  python3 scripts/aura_gate.py IMG.png [IMG2.png ...] \
      [--overlay-dir DIR] [--json OUT.json] [--nonwhite PATH ...] \
      [--fail-thresh 0.20] [--grad-thresh 10] [--near-px 6] [--max-dist 30]

  python3 scripts/aura_gate.py --self-test
      Generates two synthetic fixtures (a crisp inked-edge cutout and a
      wide-glow aura cutout) in a temp dir and prints their metrics, to show
      the gate discriminates a known-clean edge from a known-aura edge.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import (
    binary_erosion,
    distance_transform_edt,
    gaussian_filter,
    label,
    sobel,
)

# Calibrated defaults (see report / WIKI for the calibration trace): these
# separate the 4 known-bad api-lane candidates (aura_index 0.36-0.52) from
# the crisp-inked reference art (aura_index 0.14, all in the known soft
# sand-wash region at the very bottom) and from a synthetic crisp-edge
# fixture (aura_index ~0).
ALPHA_THRESH = 250      # pixel counts as "opaque" (avoids antialiasing fringe noise)
GRAD_THRESH = 10.0      # Sobel gradient magnitude counted as a "strong edge"
NEAR_PX = 6             # aura-flag a boundary pixel if no strong edge within this many px
MAX_DIST = 30           # cap on how far inward we search
GAUSS_SIGMA = 0.7       # mild pre-blur so single-pixel noise doesn't count as an "edge"
FAIL_THRESH = 0.20      # aura_index above this -> verdict FAIL


def load_mask_gray(path: Path, nonwhite: bool = None, alpha_thresh: int = ALPHA_THRESH):
    """Load an image and return (mask, gray) where mask is the boolean
    "opaque subject" foreground and gray is a luminance array for gradient
    analysis. Auto-detects a flattened white-background image (no real
    alpha channel) and synthesizes a non-white mask for it, unless
    `nonwhite` is explicitly set True/False."""
    im = Image.open(path)
    has_alpha = "A" in im.getbands()
    im_rgba = im.convert("RGBA")
    arr = np.array(im_rgba).astype(np.float64)
    rgb = arr[..., :3]
    alpha = arr[..., 3]
    auto_nonwhite = (not has_alpha) or bool(alpha.min() >= 250)
    use_nonwhite = auto_nonwhite if nonwhite is None else nonwhite
    if use_nonwhite:
        # No usable alpha (flattened/white-bg image): treat clearly
        # non-white pixels as the "opaque subject".
        diff = 255 - rgb.min(axis=-1)
        mask = diff > 12
    else:
        mask = alpha >= alpha_thresh
    gray = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    return mask, gray, use_nonwhite


def _main_bg_component(mask: np.ndarray) -> np.ndarray:
    """Boolean mask of the single largest background (non-subject) blob —
    the surrounding canvas — so small enclosed gaps between fine details
    (branch tips, texture holes) don't dilute the outer-contour aura
    measurement."""
    bg = ~mask
    lbl, n = label(bg, structure=np.ones((3, 3)))
    if n == 0:
        return np.zeros_like(mask, dtype=bool)
    sizes = np.bincount(lbl.ravel())
    sizes[0] = 0
    return lbl == sizes.argmax()


def aura_metrics(
    mask: np.ndarray,
    gray: np.ndarray,
    grad_thresh: float = GRAD_THRESH,
    near_px: int = NEAR_PX,
    max_dist: int = MAX_DIST,
    sigma: float = GAUSS_SIGMA,
    main_bg_only: bool = True,
):
    """Core measurement. Returns a dict of scalar metrics plus the raw
    per-boundary-pixel arrays needed to draw the debug overlay."""
    gray_s = gaussian_filter(gray, sigma=sigma)
    gx = sobel(gray_s, axis=1)
    gy = sobel(gray_s, axis=0)
    gmag = np.hypot(gx, gy) / 4.0  # normalize Sobel's built-in x4 kernel gain

    # "valid" = pixel whose full 3x3 neighborhood is itself inside the mask,
    # so its gradient reading can't be contaminated by the antialiasing
    # fringe or background pixels just outside the true subject.
    valid = binary_erosion(mask, structure=np.ones((3, 3)))

    dist, (iy, ix) = distance_transform_edt(mask, return_distances=True, return_indices=True)
    boundary = mask & ~binary_erosion(mask, structure=np.ones((3, 3)))

    if main_bg_only:
        main_bg = _main_bg_component(mask)
        bys, bxs = np.nonzero(boundary)
        keep = main_bg[iy[bys, bxs], ix[bys, bxs]]
        bys, bxs = bys[keep], bxs[keep]
    else:
        bys, bxs = np.nonzero(boundary)

    n = len(bys)
    h, w = mask.shape
    if n == 0:
        return {
            "boundary_px": 0, "aura_index": 0.0, "mean_band_width": 0.0,
            "median_band_width": 0.0, "hit_rate": 0.0,
            "_bys": bys, "_bxs": bxs, "_found": np.array([]), "_uy": np.array([]), "_ux": np.array([]),
        }

    d = np.maximum(dist[bys, bxs], 1e-6)
    uy = (bys - iy[bys, bxs]) / d
    ux = (bxs - ix[bys, bxs]) / d

    found = np.full(n, float(max_dist))
    hit = np.zeros(n, dtype=bool)
    for t in range(1, max_dist + 1):
        sy = np.clip(np.round(bys + t * uy).astype(int), 0, h - 1)
        sx = np.clip(np.round(bxs + t * ux).astype(int), 0, w - 1)
        v = valid[sy, sx]
        g = gmag[sy, sx]
        newly = (~hit) & v & (g > grad_thresh)
        found[newly] = t
        hit |= newly

    aura_flag = found > near_px
    return {
        "boundary_px": int(n),
        "aura_index": round(float(aura_flag.mean()), 4),
        "mean_band_width": round(float(found.mean()), 3),
        "median_band_width": float(np.median(found)),
        "hit_rate": round(float(hit.mean()), 4),
        "_bys": bys, "_bxs": bxs, "_found": found, "_uy": uy, "_ux": ux,
    }


def make_overlay(path: Path, mask: np.ndarray, metrics: dict, near_px: int = NEAR_PX) -> Image.Image:
    """Debug overlay: the source composited on mid-gray, boundary pixels
    colored green (clean) / red (aura), and the detected glow band (from
    the boundary to the first strong-gradient pixel) for every flagged
    pixel shaded translucent magenta."""
    im = Image.open(path).convert("RGBA")
    base = Image.new("RGBA", im.size, (128, 128, 128, 255))
    base = Image.alpha_composite(base, im).convert("RGB")
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ov = np.array(overlay)

    bys, bxs, found, uy, ux = (metrics["_bys"], metrics["_bxs"], metrics["_found"],
                               metrics["_uy"], metrics["_ux"])
    h, w = mask.shape
    for by, bx, f, dy, dx in zip(bys, bxs, found, uy, ux):
        is_aura = f > near_px
        color = (255, 0, 60, 255) if is_aura else (0, 200, 90, 255)
        if is_aura:
            for t in range(1, int(f) + 1):
                sy = int(round(by + t * dy)); sx = int(round(bx + t * dx))
                if 0 <= sy < h and 0 <= sx < w:
                    ov[sy, sx] = (255, 0, 220, 90)
        ov[by, bx] = color

    draw_overlay = Image.fromarray(ov, "RGBA")
    out = Image.alpha_composite(base.convert("RGBA"), draw_overlay)
    return out.convert("RGB")


def score_image(path: Path, nonwhite: bool = None, overlay_path: Path = None,
                 fail_thresh: float = FAIL_THRESH, **kw) -> dict:
    mask, gray, used_nonwhite = load_mask_gray(path, nonwhite=nonwhite)
    metrics = aura_metrics(mask, gray, **kw)
    result = {
        "path": str(path),
        "mode_used": "nonwhite" if used_nonwhite else "alpha",
        "boundary_px": metrics["boundary_px"],
        "aura_index": metrics["aura_index"],
        "mean_band_width": metrics["mean_band_width"],
        "median_band_width": metrics["median_band_width"],
        "hit_rate": metrics["hit_rate"],
        "verdict": "FAIL" if metrics["aura_index"] > fail_thresh else "PASS",
    }
    if overlay_path is not None:
        overlay = make_overlay(path, mask, metrics, near_px=kw.get("near_px", NEAR_PX))
        overlay_path.parent.mkdir(parents=True, exist_ok=True)
        overlay.save(overlay_path)
        result["overlay"] = str(overlay_path)
    return result


# --------------------------------------------------------------------------
# Self-test: synthetic crisp-edge fixture (should PASS) vs synthetic aura
# fixture (should FAIL), to calibrate/prove the gate works before trusting
# it on real candidates.
# --------------------------------------------------------------------------
def _make_synthetic_crisp(size=400):
    """A rounded-square subject with a hard binary alpha edge and a dark
    ink outline painted right at that edge — the "no aura" case."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = size // 3
    cx = cy = size // 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(230, 160, 90, 255))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(40, 20, 10, 255), width=6)
    return im


def _make_synthetic_aura(size=400, glow_px=26):
    """Same disc and ink edge, but surrounded by a smooth glow ring that is
    FULLY OPAQUE out to `glow_px` beyond the true inked edge, fading from
    the edge color to a paler tint with no internal gradient structure —
    the aura defect being detected."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    arr = np.array(im)
    cx = cy = size // 2
    r = size // 3
    yy, xx = np.mgrid[0:size, 0:size]
    rr = np.hypot(yy - cy, xx - cx)
    inside = rr <= r
    ring = (rr > r) & (rr <= r + glow_px)
    t = np.clip((rr - r) / glow_px, 0, 1)
    base_color = np.array([230, 160, 90])
    pale_color = np.array([245, 235, 225])
    for c in range(3):
        arr[..., c] = np.where(inside, base_color[c],
                                np.where(ring, (base_color[c] * (1 - t) + pale_color[c] * t).astype(np.uint8), 0))
    arr[..., 3] = np.where(inside | ring, 255, 0).astype(np.uint8)
    im = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(im)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(40, 20, 10, 255), width=6)
    return im


def self_test():
    tmp = Path(tempfile.mkdtemp(prefix="aura_gate_selftest_"))
    crisp_path = tmp / "synthetic_crisp.png"
    aura_path = tmp / "synthetic_aura.png"
    _make_synthetic_crisp().save(crisp_path)
    _make_synthetic_aura().save(aura_path)
    print(f"fixtures written to {tmp}")
    ok = True
    for label_, p in [("synthetic_crisp (expect PASS)", crisp_path),
                      ("synthetic_aura (expect FAIL)", aura_path)]:
        r = score_image(p, overlay_path=tmp / f"{p.stem}-overlay.png")
        print(f"  {label_}: aura_index={r['aura_index']} mean_band_width={r['mean_band_width']} "
              f"verdict={r['verdict']} overlay={r['overlay']}")
    r_crisp = score_image(crisp_path)
    r_aura = score_image(aura_path)
    if r_crisp["verdict"] != "PASS":
        print("SELF-TEST FAILED: crisp synthetic fixture did not PASS"); ok = False
    if r_aura["verdict"] != "FAIL":
        print("SELF-TEST FAILED: aura synthetic fixture did not FAIL"); ok = False
    if ok:
        print("SELF-TEST OK: gate separates a crisp inked edge from a painted aura.")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="*", type=Path)
    ap.add_argument("--overlay-dir", type=Path, default=None)
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--nonwhite", nargs="*", default=[], help="paths (from `images`) to force non-white-bg mode")
    ap.add_argument("--fail-thresh", type=float, default=FAIL_THRESH)
    ap.add_argument("--grad-thresh", type=float, default=GRAD_THRESH)
    ap.add_argument("--near-px", type=int, default=NEAR_PX)
    ap.add_argument("--max-dist", type=int, default=MAX_DIST)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        ok = self_test()
        sys.exit(0 if ok else 1)

    if not args.images:
        ap.error("provide at least one image, or use --self-test")

    force_nonwhite = {str(Path(p)) for p in args.nonwhite}
    results = []
    for img in args.images:
        nonwhite = True if str(img) in force_nonwhite else None
        overlay_path = None
        if args.overlay_dir is not None:
            overlay_path = args.overlay_dir / f"{img.stem}-aura-overlay.png"
        r = score_image(
            img, nonwhite=nonwhite, overlay_path=overlay_path, fail_thresh=args.fail_thresh,
            grad_thresh=args.grad_thresh, near_px=args.near_px, max_dist=args.max_dist,
        )
        results.append(r)
        print(f"{img.name:55s} aura_index={r['aura_index']:.4f}  "
              f"mean_band_width={r['mean_band_width']:6.2f}  verdict={r['verdict']}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, indent=2))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
