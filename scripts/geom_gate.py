#!/usr/bin/env python3
"""Deterministic geometry HARD-GATE — runs BEFORE any VLM judge.

The single highest-ROI check in the die-cut-panel pipeline: cheap, deterministic,
and refuses obviously-broken candidates (big empty gaps, art bleeding into a
cutout, keep-clear zones painted over) so the expensive VLM judge only ever sees
geometrically plausible art.

What it measures (all reported as JSON, thresholds applied at the end):

- fill_inside_contour : fraction of the panel-contour INTERIOR that is covered by
  art (i.e. not background). A good full-bleed gen fills nearly all of it; a low
  value means a big empty gap (often the bottom). This is the gated metric.
- overflow_outside_contour : fraction of all art pixels that fall OUTSIDE the
  contour. Full-bleed gens legitimately overflow the die line a little, so this
  is REPORTED, not auto-failed (unless it is egregious -> --overflow-max).
- edge_iou : IoU of the candidate's filled (art) region vs the panel mask. A
  blunt shape-agreement number; reported, gated loosely.
- per_role checks (only where determinable from the SVG):
    * internal_cutout / hole -> should be EMPTY: art coverage inside it must be
      LOW (a die-cut void can't have art in it). Failing one fails the gate.
    * keep_clear / no_focal_motif zone -> should be CLEAR-ish: high coverage is
      only a warning (these are "no recognizable motif", not "no paint"), unless
      coverage is extreme.

Mapping: the panel mask (contour-mask.png, interior=white) is resized to the
candidate. SVG roles (cutouts / keep-clear) are mapped from SVG body-bbox onto
the panel-mask interior bbox with the same non-uniform fit geom_iou.py uses, so
candidate / mask / SVG never need to be the same resolution.

CLI:
  python3 scripts/geom_gate.py --cand PNG --svg SVG [--mask PNG] [--thresh 0.82]

Exit code: 0 on PASS, 1 on FAIL (so it can gate a shell pipeline / loop).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


# ---------------------------------------------------------------------------
# art / background detection
# ---------------------------------------------------------------------------
def art_mask(rgb: np.ndarray, white_thresh: int = 238, sat_thresh: int = 14) -> np.ndarray:
    """Boolean mask of pixels that carry ART (i.e. are NOT plain background).

    Background is near-white and near-grey (low saturation, high value). A pixel
    is art if it is either not bright enough OR has visible chroma.
    """
    rgb = rgb.astype(np.int16)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    bright = mn >= white_thresh          # all channels bright -> whitish
    low_sat = (mx - mn) <= sat_thresh    # little chroma -> grey/white
    background = bright & low_sat
    return ~background


# ---------------------------------------------------------------------------
# panel interior mask (from contour-mask.png), resized to candidate
# ---------------------------------------------------------------------------
def load_panel_mask(mask_path: Path, size_wh: tuple[int, int]) -> np.ndarray:
    from PIL import Image

    m = Image.open(mask_path).convert("L").resize(size_wh, Image.NEAREST)
    a = np.asarray(m)
    interior = a > 127
    # Defensive: if the file is inverted (interior dark), flip so interior is the
    # blob that owns the image CENTER, not the border. Border-frac alone is not
    # enough: a tight-cropped panel mask (controlmap output, body bbox-cropped and
    # touching left/right/bottom edges) has a mostly-white border yet is NOT
    # inverted — flipping it zeroed every metric (bug found 2026-07-05).
    H, W = interior.shape
    border = np.zeros_like(interior)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    border_interior_frac = interior[border].mean()
    center_interior_frac = interior[H // 3: 2 * H // 3, W // 3: 2 * W // 3].mean()
    if border_interior_frac > 0.5 and center_interior_frac < 0.5:
        # border claims "interior" while the center doesn't -> truly inverted
        interior = ~interior
    return interior


def bbox_of(mask: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(mask)
    if not len(xs):
        return 0, 0, mask.shape[1], mask.shape[0]
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


# ---------------------------------------------------------------------------
# SVG role polygons -> candidate-pixel masks (bbox-fit, like geom_iou.py)
# ---------------------------------------------------------------------------
def role_masks_from_svg(svg_path: Path, panel_interior: np.ndarray, void_min: float = 0.5):
    """Return (cutouts, keep_clear) lists of boolean masks in candidate pixels.

    Mapping: SVG geometry is fit from the OUTER-CONTOUR bbox (the panel die line)
    onto the contour-mask interior bbox — NOT the union with paintable_region,
    whose bbox can extend past the contour and skew the fit.

    Cutouts are FILTERED to real die-cut voids: each SVG `internal_cutout` is kept
    only if the contour-mask confirms it as a hole (its region is mostly EXTERIOR
    in the panel mask, void_frac >= void_min). This rejects the common SVG
    false-positive where decorative top/edge strips are heuristically tagged as
    cutouts but are solid panel that a full-bleed gen legitimately paints over.
    Returns ([], []) if the SVG can't be parsed — the gate then runs mask-only.
    """
    try:
        import svg_classify as C
        from PIL import Image, ImageDraw
    except Exception:
        return [], []

    try:
        _, shapes = C.extract_shapes(svg_path)
        shapes = C.classify(shapes)
    except Exception:
        return [], []

    contour = [s for s in shapes if s.polygon is not None and s.role == "outer_contour"]
    body = contour or [s for s in shapes if s.polygon is not None and s.role == "paintable_region"]
    cuts = [s for s in shapes if s.polygon is not None and s.role == "internal_cutout"]
    keep = [s for s in shapes if s.polygon is not None and s.role in ("keep_clear_zone", "no_focal_motif_zone")]
    if not body:
        return [], []

    cx0 = min(s.bounds[0] for s in body); cy0 = min(s.bounds[1] for s in body)
    cx1 = max(s.bounds[2] for s in body); cy1 = max(s.bounds[3] for s in body)
    if cx1 <= cx0 or cy1 <= cy0:
        return [], []

    L, T, R, B = bbox_of(panel_interior)
    H, W = panel_interior.shape
    sx = (R - L) / (cx1 - cx0)
    sy = (B - T) / (cy1 - cy0)

    def f(x, y):
        return (L + (x - cx0) * sx, T + (y - cy0) * sy)

    def poly_to_mask(poly) -> np.ndarray:
        im = Image.new("L", (W, H), 0)
        ImageDraw.Draw(im).polygon([f(x, y) for x, y in poly.exterior.coords], fill=255)
        return np.asarray(im) > 127

    exterior = ~panel_interior
    # A true die-cut HOLE is an exterior island ENCLOSED by panel — NOT an edge
    # notch that opens onto the outer background. Full-bleed art legitimately paints
    # past edge notches (they get cut away), so only enclosed islands must be empty.
    # The border-touching exterior connected-component(s) = outer background; any
    # other exterior component = an enclosed hole.
    try:
        import cv2
        _, labels = cv2.connectedComponents(exterior.astype(np.uint8))
        border_labels = set(np.unique(np.concatenate(
            [labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])).tolist())
        enclosed_ext = exterior & ~np.isin(labels, list(border_labels))
    except Exception:
        enclosed_ext = np.zeros_like(exterior)

    cut_masks = []
    for s in cuts:
        m = poly_to_mask(s.polygon)
        n = int(m.sum())
        if n == 0:
            continue  # maps outside the interior bbox — not a checkable void here
        void_overlap = int((m & exterior).sum())
        if void_overlap == 0:
            continue
        void_frac = void_overlap / n
        enclosed_frac = float((m & enclosed_ext).sum()) / void_overlap
        # keep only confirmed ENCLOSED die-cut voids; reject edge notches (which a
        # full-bleed gen rightly paints over) — this was a false-positive source.
        if void_frac >= void_min and enclosed_frac >= 0.5:
            cut_masks.append(m)
    keep_masks = [poly_to_mask(s.polygon) for s in keep]
    return cut_masks, keep_masks


def coverage(art: np.ndarray, region: np.ndarray) -> float:
    denom = int(region.sum())
    if denom == 0:
        return 0.0
    return float((art & region).sum()) / denom


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cand", required=True, type=Path, help="candidate PNG")
    ap.add_argument("--svg", type=Path, help="panel SVG (for per-role checks); omit for a mask-authoritative "
                    "run on templates with no drawn panel contour (city-skyline narrows) — --mask required then")
    ap.add_argument("--mask", type=Path, help="contour-mask PNG (interior=white); default: <svg dir up>/contour-mask.png")
    ap.add_argument("--thresh", type=float, default=0.82, help="min fill_inside_contour to PASS (default 0.82)")
    ap.add_argument("--overflow-max", type=float, default=0.45,
                    help="overflow fraction above which a full-bleed is flagged as egregious (default 0.45)")
    ap.add_argument("--cutout-max", type=float, default=0.35,
                    help="max art coverage allowed inside a cutout/hole before FAIL (default 0.35)")
    ap.add_argument("--keepclear-max", type=float, default=0.92,
                    help="art coverage in a keep-clear zone above which it is flagged (warning unless --keepclear-fail)")
    ap.add_argument("--keepclear-fail", action="store_true", help="treat keep-clear over-coverage as a hard FAIL too")
    ap.add_argument("--edge-iou-min", type=float, default=0.55, help="min edge_iou before flagging (warning)")
    ap.add_argument("--json-out", type=Path, help="write the JSON report here")
    a = ap.parse_args()

    from PIL import Image

    cand_path = a.cand if a.cand.is_absolute() else ROOT / a.cand
    svg_path = (a.svg if a.svg.is_absolute() else ROOT / a.svg) if a.svg else None
    if a.mask:
        mask_path = a.mask if a.mask.is_absolute() else ROOT / a.mask
    elif svg_path:
        # default: contour-mask.png next to the SVG's task dir (source/foo.svg -> ../contour-mask.png)
        mask_path = svg_path.parent.parent / "contour-mask.png"
    else:
        ap.error("--mask is required when --svg is omitted (mask-authoritative run)")

    rgb = np.asarray(Image.open(cand_path).convert("RGB"))
    H, W = rgb.shape[:2]
    art = art_mask(rgb)

    if not mask_path.exists():
        print(f"FAIL: panel mask not found: {mask_path}", file=sys.stderr)
        return 1
    interior = load_panel_mask(mask_path, (W, H))
    exterior = ~interior

    # ---- core metrics -------------------------------------------------------
    interior_n = int(interior.sum())
    art_n = int(art.sum())
    fill_inside = float((art & interior).sum()) / interior_n if interior_n else 0.0
    overflow_outside = float((art & exterior).sum()) / art_n if art_n else 0.0

    inter = int((art & interior).sum())
    union = int((art | interior).sum())
    edge_iou = inter / union if union else 0.0

    # ---- per-role checks ----------------------------------------------------
    # mask-authoritative run (no SVG): the mask IS the geometry contract; per-role
    # checks are skipped — templates with no drawn panel contour have no role
    # polygons to map anyway (city-skyline narrows).
    cut_masks, keep_masks = role_masks_from_svg(svg_path, interior) if svg_path else ([], [])
    cutouts = []
    for i, cm in enumerate(cut_masks, 1):
        # a confirmed die-cut void is EXTERIOR in the panel mask, so measure art
        # over the void region itself — art there means the gen painted the hole.
        cov = coverage(art, cm)
        cutouts.append({"i": i, "art_coverage": round(cov, 4), "ok": cov <= a.cutout_max})
    keepclear = []
    for i, km in enumerate(keep_masks, 1):
        # keep-clear zones live inside the panel; score art over the in-panel part.
        region = km & interior
        if not region.any():
            region = km
        cov = coverage(art, region)
        keepclear.append({"i": i, "art_coverage": round(cov, 4), "ok": cov <= a.keepclear_max})

    # ---- verdict ------------------------------------------------------------
    fails: list[str] = []
    warnings: list[str] = []

    if fill_inside < a.thresh:
        fails.append(f"fill_inside_contour {fill_inside:.3f} < thresh {a.thresh:.2f} (big empty gap inside the panel)")
    bad_cuts = [c["i"] for c in cutouts if not c["ok"]]
    if bad_cuts:
        fails.append(f"art inside cutout/hole(s) {bad_cuts} > {a.cutout_max:.2f} (die-cut void must be empty)")
    bad_keep = [k["i"] for k in keepclear if not k["ok"]]
    if bad_keep:
        msg = f"keep-clear zone(s) {bad_keep} art_coverage > {a.keepclear_max:.2f}"
        (fails if a.keepclear_fail else warnings).append(msg)

    if overflow_outside > a.overflow_max:
        warnings.append(f"overflow_outside_contour {overflow_outside:.3f} > {a.overflow_max:.2f} (heavy bleed past die line)")
    if edge_iou < a.edge_iou_min:
        warnings.append(f"edge_iou {edge_iou:.3f} < {a.edge_iou_min:.2f} (filled region disagrees with panel shape)")

    verdict = "PASS" if not fails else "FAIL"

    report = {
        "candidate": str(cand_path),
        "svg": str(svg_path) if svg_path else None,
        "mask": str(mask_path),
        "candidate_size": [W, H],
        "thresh": a.thresh,
        "fill_inside_contour": round(fill_inside, 4),
        "overflow_outside_contour": round(overflow_outside, 4),
        "edge_iou": round(edge_iou, 4),
        "per_role": {
            "cutouts": cutouts,
            "keep_clear": keepclear,
            "note": ("no per-role polygons resolved from SVG (mask-only run)"
                     if not cut_masks and not keep_masks else ""),
        },
        "verdict": verdict,
        "fails": fails,
        "warnings": warnings,
    }

    print(json.dumps(report, indent=2))
    if a.json_out:
        jp = a.json_out if a.json_out.is_absolute() else ROOT / a.json_out
        jp.parent.mkdir(parents=True, exist_ok=True)
        jp.write_text(json.dumps(report, indent=2) + "\n")
        print(f"json -> {jp}", file=sys.stderr)

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
