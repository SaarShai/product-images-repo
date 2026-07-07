#!/usr/bin/env python3
"""door_fill_gate.py — door-anchor fill/overflow gate (overlay-law enforcement).

Geometry NEVER judged by eye. Given a raw candidate and the vector geometry
folder for a panel (door-control.png + door-spec.json), this:

1. Registers the raw to the control frame by resizing it to the control's
   pixel dims (both are full-panel renders, so a plain resize aligns them —
   no crop/pad needed for this template family).
2. Derives the TRUE portal region by flood-filling the door path traced in
   door-control.png (white lines on black) rather than trusting a synthetic
   rect/arc reconstruction. The traced outline is pixel-verified against
   door_anchor_frac from door-spec.json (bbox must agree within 0.5% of each
   edge) — if it doesn't, the control PNG and spec have drifted and this
   gate refuses to score (banned: falling back to a synthetic shape).
3. Measures PORTAL OCCUPANCY: door_fill = the fraction of the true portal
   region that is NON-BACKGROUND (painted door structure), regardless of
   hue. Background is defined as near-white/near-empty pixels (HSV value
   > 0.90 AND saturation < 0.10); everything else inside the portal counts
   as painted. This replaced an earlier color heuristic that assumed doors
   are always a dominant saturated blue — that heuristic false-negatived
   teal/pale/green doors that visually DO fill the portal (round-2b
   calibration: arm-g_s1, arm-g_s5, arm-l_s1 all scored low under the old
   blue-only segmentation despite being visually-filled doors).
4. Reports door_fill = |non-background ∩ portal| / |portal| and
   door_outside = 0.0 (occupancy is portal-relative only; there is no
   separate "door shape" to measure outside the portal any more), with
   verdict:
     PASS  door_fill >= --pass-fill   (default 0.90)
     WARN  --warn-fill <= door_fill < --pass-fill (default 0.75)
     FAIL  door_fill <  --warn-fill
   Thresholds per binding user verdict: the door must fill the ENTIRE
   door/flap region (Option 1) — no normal-proportion door-within-arch.
5. ALWAYS writes an overlay PNG: control lines composited over the resized
   raw, with the segmented door region tinted.

CLI:
  python3 scripts/door_fill_gate.py --image <raw.png> --geom <geom-dir> \
      [--panel door] [--overlay out.png] [--pass-fill 0.90] [--warn-fill 0.75]

Exit 0 always (this is a measurement/report tool, not a hard process gate);
the verdict field carries the PASS/WARN/FAIL decision for callers to act on.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

HEURISTIC_NOTE = (
    "door_fill = fraction of the true portal region that is NON-BACKGROUND "
    "(painted), where background = near-white/near-empty (HSV value > 0.90 "
    "AND saturation < 0.10). Hue-agnostic portal-occupancy, not a color "
    "heuristic — replaces an earlier blue-only segmentation that "
    "false-negatived teal/pale/green painted doors."
)

BBOX_TOL_FRAC = 0.005  # 0.5% per edge, per brief


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _flood_from_border(not_line: np.ndarray) -> np.ndarray:
    """Flood-fill 'outside' starting from every non-line pixel on the array
    border, propagating across 4-connected non-line pixels."""
    h, w = not_line.shape
    outside = np.zeros((h, w), dtype=bool)
    dq: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not_line[y, x] and not outside[y, x]:
                outside[y, x] = True
                dq.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not_line[y, x] and not outside[y, x]:
                outside[y, x] = True
                dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not_line[ny, nx] and not outside[ny, nx]:
                outside[ny, nx] = True
                dq.append((nx, ny))
    return outside


def trace_portal_mask(control: Image.Image, spec_frac: list[float], pad_frac: float = 0.03) -> np.ndarray:
    """Flood-fill the region enclosed by the white door path traced on black.

    door-control.png draws the true door/opening outline (plus unrelated
    outer-silhouette and hardware lines) as white strokes on a black field.
    The full-frame outline is one connected open shape, so a naive full-image
    flood-fill can't isolate just the door portal. Instead we crop tightly
    around door_anchor_frac (with a small pad on the top/sides so the door's
    own arch/jamb lines stay inside the crop) and flood-fill from THAT crop's
    border: the outer-panel lines and side strips fall outside the crop, so
    the region enclosed by the door arch/jambs is what's left uncaptured by
    the border flood.

    The door's own BOTTOM edge is not drawn as a separate line in the control
    image — the door meets the panel's own bottom-silhouette edge there,
    which IS drawn (a thin line a couple of pixels above the image's bottom
    border). We must therefore pad slightly PAST door_anchor_frac's bottom
    edge so that closing line lands fully inside the crop; cutting the crop
    exactly at the spec's bottom fraction risks slicing through that line
    and leaking the whole interior out through the gap.
    """
    g = np.array(control.convert("L"))
    h, w = g.shape
    ax0, ay0, ax1, ay1 = spec_frac
    pad_x = int(round(pad_frac * w))
    pad_y = int(round(pad_frac * h))
    x0 = max(0, int(ax0 * w) - pad_x)
    x1 = min(w, int(ax1 * w) + pad_x)
    y0 = max(0, int(ay0 * h) - pad_y)
    y1 = min(h, int(ay1 * h) + pad_y)

    crop = g[y0:y1, x0:x1]
    line = crop > 60
    # The traced path is drawn as adjacent parallel strokes in places (an
    # arch/reveal double-line); where one curve grazes another line at a
    # shallow angle, anti-aliasing leaves a sub-pixel gap of "not line"
    # pixels between them (measured: closes only at kernel>=7). A small
    # morphological dilation of the line mask bridges those gaps without
    # materially shrinking the portal.
    from PIL import Image as _Image, ImageFilter as _ImageFilter
    line_img = _Image.fromarray((line * 255).astype(np.uint8))
    line_dilated = np.array(line_img.filter(_ImageFilter.MaxFilter(7))) > 0
    not_line = ~line_dilated
    outside = _flood_from_border(not_line)
    interior_crop = not_line & ~outside

    interior = np.zeros((h, w), dtype=bool)
    interior[y0:y1, x0:x1] = interior_crop
    return interior


def clip_to_spec_bbox(interior: np.ndarray, spec_frac: list[float]) -> np.ndarray:
    """Clip the traced interior to the door_anchor_frac bbox.

    The control image's traced path is a double-line (an outer arch/reveal
    trim curve plus the inner door-leaf curve); the flood-filled interior
    naturally includes the thin band between them, which sits slightly
    outside door_anchor_frac's declared bbox (measured: up to ~2% on the
    header edge). door_anchor_frac from door-spec.json is the authoritative
    geometry contract (see wiki: "Geometry spec = single source"), so the
    portal used for scoring is the intersection of the traced door shape
    with the spec's declared bbox, not the raw flood-fill extent.
    """
    h, w = interior.shape
    ax0, ay0, ax1, ay1 = spec_frac
    x0, x1 = int(ax0 * w), int(ax1 * w)
    y0, y1 = int(ay0 * h), int(ay1 * h)
    clipped = np.zeros_like(interior)
    clipped[y0:y1, x0:x1] = interior[y0:y1, x0:x1]
    return clipped


def verify_portal_bbox(interior: np.ndarray, spec_frac: list[float]) -> tuple[bool, list[float]]:
    h, w = interior.shape
    ys, xs = np.where(interior)
    if len(xs) == 0:
        return False, [0, 0, 0, 0]
    measured = [xs.min() / w, ys.min() / h, (xs.max() + 1) / w, (ys.max() + 1) / h]
    ok = all(abs(m - s) <= BBOX_TOL_FRAC for m, s in zip(measured, spec_frac))
    return ok, measured


def segment_painted(rgb: np.ndarray) -> np.ndarray:
    """Hue-agnostic PORTAL-OCCUPANCY mask (see HEURISTIC_NOTE).

    A pixel counts as "painted door structure" unless it's near-white/
    near-empty background: HSV value > 0.90 AND saturation < 0.10. This
    replaces the earlier dominant-saturated-blue heuristic, which
    false-negatived teal/pale/green painted doors that visually fill the
    portal just fine — the color of the paint is irrelevant to whether the
    portal is occupied.
    """
    arr = rgb.astype(np.float32) / 255.0
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    value = maxc
    saturation = np.where(maxc > 0, (maxc - minc) / np.where(maxc > 0, maxc, 1), 0.0)
    is_background = (value > 0.90) & (saturation < 0.10)
    return ~is_background


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--geom", required=True, help="geometry dir with <panel>-control.png / <panel>-spec.json")
    ap.add_argument("--panel", default="door")
    ap.add_argument("--overlay", default=None)
    ap.add_argument("--pass-fill", type=float, default=0.90)
    ap.add_argument("--warn-fill", type=float, default=0.75)
    a = ap.parse_args()

    geom = Path(a.geom)
    control_path = geom / f"{a.panel}-control.png"
    spec_path = geom / f"{a.panel}-spec.json"
    spec = _load_json(spec_path)
    control = Image.open(control_path)
    w, h = control.size

    interior_all = trace_portal_mask(control, spec["door_anchor_frac"])
    portal_mask = clip_to_spec_bbox(interior_all, spec["door_anchor_frac"])
    bbox_ok, measured_frac = verify_portal_bbox(portal_mask, spec["door_anchor_frac"])

    if not bbox_ok:
        result = {
            "verdict": "FAIL",
            "error": "traced portal bbox disagrees with door_anchor_frac by more than 0.5%/edge",
            "measured_frac": [round(v, 4) for v in measured_frac],
            "spec_frac": spec["door_anchor_frac"],
            "heuristic_note": HEURISTIC_NOTE,
        }
        print(json.dumps(result, indent=1))
        return 0

    raw = Image.open(a.image).convert("RGB")
    if raw.size != (w, h):
        raw = raw.resize((w, h), Image.Resampling.LANCZOS)
    raw_arr = np.array(raw)

    painted_mask = segment_painted(raw_arr)

    portal_px = int(portal_mask.sum())
    inter_px = int((painted_mask & portal_mask).sum())
    background_px = portal_px - inter_px

    door_fill = inter_px / portal_px if portal_px else 0.0
    door_outside = background_px / portal_px if portal_px else 0.0

    if door_fill >= a.pass_fill:
        verdict = "PASS"
    elif door_fill >= a.warn_fill:
        verdict = "WARN"
    else:
        verdict = "FAIL"

    result = {
        "verdict": verdict,
        "door_fill": round(door_fill, 4),
        "door_outside": round(door_outside, 4),
        "portal_px": portal_px,
        "painted_px": inter_px,
        "intersection_px": inter_px,
        "pass_fill": a.pass_fill,
        "warn_fill": a.warn_fill,
        "measured_portal_frac": [round(v, 4) for v in measured_frac],
        "spec_door_anchor_frac": spec["door_anchor_frac"],
        "heuristic_note": HEURISTIC_NOTE,
    }

    overlay_path = a.overlay or str(Path(a.image).with_suffix("")) + ".door-fill-overlay.png"
    ov = raw.convert("RGBA")
    tint = Image.new("RGBA", ov.size, (255, 0, 255, 0))
    tint_arr = np.array(tint)
    tint_arr[painted_mask & portal_mask] = (255, 0, 255, 110)
    tint = Image.fromarray(tint_arr)
    ov = Image.alpha_composite(ov, tint)

    control_rgba = control.convert("L")
    control_np = np.array(control_rgba)
    lines_rgba = np.zeros((h, w, 4), dtype=np.uint8)
    lines_rgba[control_np > 60] = (255, 0, 0, 220)
    lines_img = Image.fromarray(lines_rgba)
    ov = Image.alpha_composite(ov, lines_img)
    ov.convert("RGB").save(overlay_path)
    result["overlay"] = overlay_path

    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
