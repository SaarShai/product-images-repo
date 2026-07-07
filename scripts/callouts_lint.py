#!/usr/bin/env python3
"""callouts_lint.py — deterministic lint on a feature-callouts YAML (ENFORCEMENT-MATRIX rows 8/10/11).

Checks, for every feature's zone_bbox_frac:
  (a) x-clearance >= 0.02 from every forbidden band in BOTH the callouts YAML's
      own header-documented bands (if present as top-level `forbidden_bands_frac`)
      AND the geometry dir's door-spec.json `forbidden_bands_frac`.
  (b) no overlap with the TRUE door-PORTAL MASK (traced from
      tasks/marriott-hospital/geometry/v3/door-control.png via
      scripts/layout_ref.py's _load_door_portal_mask — never a synthetic
      door_anchor_frac bbox; the portal is arch-shaped and narrower than its
      own bbox at the top corners, so a zone can sit inside the anchor bbox's
      corner without touching a single portal pixel), UNLESS the feature's
      layer is 'architecture' AND its zone is fully ABOVE the anchor top
      (zone y1 <= anchor y0 from door-spec.json). A row may also declare
      `dodge_portal: true` (see below) to downgrade a real portal-mask
      overlap to an advisory note instead of a hard violation.
      Live trace (layout_ref._load_door_portal_mask) is preferred; falls back
      to the cached tasks/workflow-rebuild/refs/demo-layout/door-portal-mask.png
      if the live trace is unavailable (e.g. scipy missing / door-control.png
      missing); if BOTH are unavailable, falls back further to the old
      door_anchor_frac BBOX check and sets a `warning` field in the report.
  (c) zone_bbox_frac is well-formed (x0<x1, y0<y1) and fully inside [0,1] on
      both axes (i.e. inside the panel frame).

`dodge_portal: true` YAML CONTRACT: a feature row may declare this when the
renderer (layout_ref._dodge_feature_boxes) guarantees its drawn shapes are
shifted clear of the portal mask at render time. For such rows, a portal
overlap detected here (against the row's AUTHORED zone_bbox_frac, pre-dodge)
is reported as an advisory note ("renderer-dodged") in the JSON, not a hard
violation — stripe-clearance (a) and bounds (c) stay HARD regardless.

CLI:
  python3 scripts/callouts_lint.py --callouts <yaml> --geom <dir>

Exit 0 PASS / 2 FAIL (violation list printed as JSON either way).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

X_CLEARANCE = 0.02

ROOT = Path(__file__).resolve().parents[1]
CACHED_PORTAL_MASK_PNG = (
    ROOT / "tasks/workflow-rebuild/refs/demo-layout/door-portal-mask.png"
)


def _load_spec(geom_dir: Path) -> dict:
    spec_path = geom_dir / "door-spec.json"
    if not spec_path.exists():
        raise SystemExit(f"callouts_lint: missing spec {spec_path}")
    return json.loads(spec_path.read_text())


def _load_portal_mask() -> tuple:
    """Return (mask, source) where mask is a boolean numpy array (True =
    portal interior) in its own native pixel grid, and source is one of
    'live-trace' / 'cached' / None (both unavailable). Prefers the live trace
    (scripts/layout_ref.py's _load_door_portal_mask, traced fresh from
    door-control.png) and falls back to the cached PNG."""
    try:
        sys.path.insert(0, str(ROOT))
        from scripts.layout_ref import _load_door_portal_mask
        mask = _load_door_portal_mask()
        return mask, "live-trace"
    except Exception:
        pass
    try:
        import numpy as np
        from PIL import Image
        if CACHED_PORTAL_MASK_PNG.exists():
            arr = np.array(Image.open(CACHED_PORTAL_MASK_PNG).convert("L"))
            return (arr > 127), "cached"
    except Exception:
        pass
    return None, None


def _zone_overlaps_portal_mask(zone, mask) -> bool:
    """Pixel-accurate overlap test: does zone_bbox_frac (x0,y0,x1,y1 in [0,1])
    intersect any True pixel of the portal mask (in the mask's own grid)?"""
    import numpy as np
    x0, y0, x1, y1 = zone
    h, w = mask.shape
    px0 = max(0, int(np.floor(x0 * w)))
    py0 = max(0, int(np.floor(y0 * h)))
    px1 = min(w, int(np.ceil(x1 * w)))
    py1 = min(h, int(np.ceil(y1 * h)))
    if px1 <= px0 or py1 <= py0:
        return False
    return bool(mask[py0:py1, px0:px1].any())


def _band_violation(zone, band, clearance=X_CLEARANCE):
    """Return a message if zone's x-range doesn't keep >=clearance from band."""
    x0, y0, x1, y1 = zone
    bx0, bx1 = band
    # zone/band don't overlap in x AND the gap is still under clearance -> flag.
    if x1 <= bx0:
        gap = bx0 - x1
    elif x0 >= bx1:
        gap = x0 - bx1
    else:
        gap = -1.0  # actual x-overlap with the band
    if gap < clearance:
        return (f"x-clearance {max(gap, 0.0):.4f} < {clearance} from forbidden "
                f"band [{bx0}, {bx1}] (zone x=[{x0}, {x1}])")
    return None


def _overlaps(a, b) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return ax0 < bx1 and ax1 > bx0 and ay0 < by1 and ay1 > by0


def lint(callouts_path: Path, geom_dir: Path) -> dict:
    doc = yaml.safe_load(callouts_path.read_text())
    spec = _load_spec(geom_dir)

    forbidden_bands = list(spec.get("forbidden_bands_frac", []))
    # also honor any bands declared directly in the YAML (belt & suspenders).
    forbidden_bands += list(doc.get("forbidden_bands_frac", []))

    anchor = spec.get("door_anchor_frac")
    portal_mask, mask_source = _load_portal_mask()
    warning = None
    if portal_mask is None:
        warning = (
            "portal mask unavailable (live-trace and cached PNG both failed) — "
            "falling back to door_anchor_frac BBOX overlap check"
        )

    violations = []
    advisories = []
    features = doc.get("features", [])
    for feat in features:
        fid = feat.get("feature_id", "<unknown>")
        zone = feat.get("zone_bbox_frac")
        if not zone or len(zone) != 4:
            violations.append(f"{fid}: missing/malformed zone_bbox_frac")
            continue
        x0, y0, x1, y1 = zone

        # (c) well-formed + inside [0,1]
        if not (x0 < x1 and y0 < y1):
            violations.append(f"{fid}: zone_bbox_frac not well-formed (x0<x1,y0<y1 required): {zone}")
        for v, name in ((x0, "x0"), (y0, "y0"), (x1, "x1"), (y1, "y1")):
            if v < 0.0 or v > 1.0:
                violations.append(f"{fid}: {name}={v} outside panel frame [0,1]")

        # (a) forbidden-band x-clearance
        for band in forbidden_bands:
            msg = _band_violation(zone, band)
            if msg:
                violations.append(f"{fid}: {msg}")

        # (b) door-portal overlap (pixel-accurate mask, or bbox fallback)
        if anchor:
            layer = feat.get("layer")
            architecture_exempt = layer == "architecture" and y1 <= anchor[1]
            if portal_mask is not None:
                hit = _zone_overlaps_portal_mask(zone, portal_mask)
            else:
                hit = _overlaps(zone, anchor)
            if hit and not architecture_exempt:
                dodge_portal = bool(feat.get("dodge_portal", False))
                if dodge_portal:
                    advisories.append(
                        f"{fid}: zone overlaps door portal ({mask_source or 'bbox-fallback'}) "
                        f"but declares dodge_portal: true — renderer-dodged, not a hard violation"
                    )
                else:
                    violations.append(
                        f"{fid}: zone overlaps door portal ({mask_source or 'bbox-fallback'}) "
                        f"(layer={layer!r}) and is not an exempt architecture-above-anchor "
                        f"feature nor declared dodge_portal: true"
                    )

    verdict = "PASS" if not violations else "FAIL"
    result = {
        "verdict": verdict,
        "callouts": str(callouts_path),
        "geom": str(geom_dir),
        "n_features": len(features),
        "violations": violations,
        "advisories": advisories,
        "portal_mask_source": mask_source,
    }
    if warning:
        result["warning"] = warning
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--callouts", required=True)
    ap.add_argument("--geom", required=True)
    a = ap.parse_args()

    result = lint(Path(a.callouts), Path(a.geom))
    print(json.dumps(result, indent=1))
    sys.exit(0 if result["verdict"] == "PASS" else 2)


if __name__ == "__main__":
    main()
