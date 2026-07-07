#!/usr/bin/env python3
"""content_gate.py — deterministic content-placement checks on a raw candidate
(ENFORCEMENT-MATRIX rows 8/10/11 companion to callouts_lint.py).

Registers the raw candidate to the panel frame by resizing it to the
door-mask.png dimensions (door-spec.json's canonical size_px), then measures:

  (1) OUTSIDE-WHITENESS — pixels OUTSIDE the door-mask body (door-mask.png,
      interior=white) must be near-white (no sky/scenery-outside-the-door
      rule). Reports the fraction of outside pixels with HSV saturation>0.12
      or value<0.85. FAIL if that fraction exceeds 0.05.

  (2) FLAP-CONTENT (ADVISORY / collection-tuned heuristic) — within the band
      from (door_anchor bottom - 4% of panel H) to (door_anchor bottom),
      measure edge-density of non-blue-dominant pixels (a crude steps/path
      detector: real doors in this collection are blue-dominant paint, so
      non-blue edges near the anchor bottom are a proxy for painted ground
      detail bleeding onto the flap). WARN above threshold.

  (3) Always writes an annotated overlay PNG (outside zone tinted red, flap
      band tinted yellow) next to the report or to --overlay if given.

CLI:
  python3 scripts/content_gate.py --image <raw> --geom <dir> [--overlay out.png]

Prints strict JSON. Exit 0 always (this is a report tool, not a hard gate) —
callers decide what to do with FAIL/WARN in the JSON `verdict` fields.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

WHITENESS_FAIL_FRAC = 0.05
SAT_THRESH = 0.12
VAL_THRESH = 0.85
FLAP_BAND_FRAC_H = 0.04
FLAP_WARN_RATIO = 1.35  # advisory: non-blue edge density inside band vs body baseline


def _rgb_to_hsv_sat_val(rgb: np.ndarray):
    """Vectorized HSV saturation/value from an (H,W,3) uint8 array, no colorsys loop."""
    arr = rgb.astype(np.float32) / 255.0
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    val = mx
    sat = np.where(mx > 0, (mx - mn) / np.where(mx == 0, 1, mx), 0.0)
    return sat, val


def _edges(gray: np.ndarray) -> np.ndarray:
    gray = gray.astype(float)
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    return gx + gy


def _blue_dominant(rgb: np.ndarray) -> np.ndarray:
    r = rgb[:, :, 0].astype(int)
    g = rgb[:, :, 1].astype(int)
    b = rgb[:, :, 2].astype(int)
    return (b > r + 8) & (b > g + 8)


def run(image_path: Path, geom_dir: Path, overlay_path: Path | None) -> dict:
    spec = json.loads((geom_dir / "door-spec.json").read_text())
    size_wh = tuple(spec["size_px"])  # [w, h]

    mask_img = Image.open(geom_dir / "door-mask.png").convert("L")
    body = np.array(mask_img.resize(size_wh, Image.NEAREST)) > 127  # True = inside body

    cand = Image.open(image_path).convert("RGB").resize(size_wh, Image.LANCZOS)
    rgb = np.array(cand)
    gray = np.array(cand.convert("L"))
    h_px, w_px = rgb.shape[0], rgb.shape[1]

    outside = ~body
    sat, val = _rgb_to_hsv_sat_val(rgb)
    colored_or_dark = (sat > SAT_THRESH) | (val < VAL_THRESH)
    n_outside = int(outside.sum())
    if n_outside > 0:
        n_bad_outside = int((colored_or_dark & outside).sum())
        outside_whiteness_frac = n_bad_outside / n_outside
    else:
        n_bad_outside = 0
        outside_whiteness_frac = 0.0
    whiteness_verdict = "FAIL" if outside_whiteness_frac > WHITENESS_FAIL_FRAC else "PASS"

    # (2) flap-content band, from door_anchor_frac in the spec
    anchor = spec.get("door_anchor_frac")
    flap_result = {"available": anchor is not None}
    flap_mask = np.zeros((h_px, w_px), dtype=bool)
    if anchor:
        ax0, ay0, ax1, ay1 = anchor
        anchor_bottom_px = ay1 * h_px
        band_top_px = max(0, anchor_bottom_px - FLAP_BAND_FRAC_H * h_px)
        y0i, y1i = int(round(band_top_px)), int(round(anchor_bottom_px))
        x0i, x1i = int(round(ax0 * w_px)), int(round(ax1 * w_px))
        y0i, y1i = max(0, y0i), min(h_px, y1i)
        x0i, x1i = max(0, x0i), min(w_px, x1i)
        flap_mask[y0i:y1i, x0i:x1i] = True

        edges = _edges(gray)
        non_blue = ~_blue_dominant(rgb)
        flap_zone = flap_mask & body
        base_zone = body & ~flap_mask
        flap_edge_px = edges[flap_zone & non_blue]
        base_edge_px = edges[base_zone & non_blue]
        ed_flap = float(flap_edge_px.mean()) if flap_edge_px.size else 0.0
        ed_base = float(base_edge_px.mean()) if base_edge_px.size else 1e-6
        ratio = ed_flap / max(ed_base, 1e-6)
        flap_verdict = "WARN" if ratio > FLAP_WARN_RATIO else "OK"
        flap_result.update({
            "band_px": [x0i, y0i, x1i, y1i],
            "edge_density_nonblue": {"flap": round(ed_flap, 2), "body": round(ed_base, 2),
                                     "ratio": round(ratio, 3)},
            "warn_ratio": FLAP_WARN_RATIO,
            "verdict": flap_verdict,
            "note": "collection-tuned heuristic (blue-dominant paint assumption); ADVISORY only",
        })
    else:
        flap_result["verdict"] = "SKIPPED"
        flap_result["note"] = "no door_anchor_frac in spec"

    # (3) overlay
    if overlay_path is None:
        overlay_path = image_path.with_name(image_path.stem + "-content-gate-overlay.png")
    ov = rgb.copy()
    ov[outside] = (0.5 * ov[outside] + 0.5 * np.array([255, 40, 40])).astype("uint8")
    if flap_mask.any():
        fz = flap_mask & body
        ov[fz] = (0.5 * ov[fz] + 0.5 * np.array([255, 220, 0])).astype("uint8")
    Image.fromarray(ov).save(overlay_path)

    return {
        "image": str(image_path),
        "geom": str(geom_dir),
        "registered_size_px": list(size_wh),
        "outside_whiteness": {
            "frac_bad_outside": round(outside_whiteness_frac, 4),
            "fail_thresh": WHITENESS_FAIL_FRAC,
            "sat_thresh": SAT_THRESH,
            "val_thresh": VAL_THRESH,
            "n_outside_px": n_outside,
            "n_bad_outside_px": n_bad_outside,
            "verdict": whiteness_verdict,
        },
        "flap_content": flap_result,
        "overlay": str(overlay_path),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--geom", required=True)
    ap.add_argument("--overlay", default=None)
    a = ap.parse_args()

    overlay = Path(a.overlay) if a.overlay else None
    result = run(Path(a.image), Path(a.geom), overlay)
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
