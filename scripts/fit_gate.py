#!/usr/bin/env python3
"""Geometry fit-gate for die-cut panel candidates (generalized from
tasks/marine-coral-panels/overlay_tool.py — that file is left untouched for
provenance; this is the reusable, spec-driven version).

Measures a candidate foreground element's placement against a panel geometry
spec: overlap with a creature/element silhouette mask (actual alpha, not
bboxes), and a border/no-crop check. All region math is driven by a
`--panel-spec` JSON (the `geometry_spec.json` format emitted by the panel
tooling), never hardcoded per-project paths.

geometry_spec.json required keys:
  ab_x           : [left, right] artboard x-bounds in doc points (uses ab_x[0])
  ab_top         : artboard top y in doc points
  render_scale   : doc-points -> render-pixels scale factor
  parts          : { "<PART_NAME>": { "cut_ltrb": [l, t, r, b], ... }, ... }
                   cut_ltrb is the part's crop box in doc points (left, top,
                   right, bottom; y grows upward like Illustrator artboards).
Part names are read from parts.keys() — never a hardcoded tuple.

Subcommands:
  check <part> <candidate.png> --render R --creature-alpha A [--cut-alpha C]
      [--scale S] [--xoff X] [--safety-px N] [--fg-thresh N]
      -> JSON metrics {band_px, creature_overlap_px, overlap_pct,
         above_floor_pct, border_...} + overlay PNG written next to candidate.

  search <part> <candidate.png> --render R --creature-alpha A
      --overlap-max PCT --scale-range LO:HI:STEP
      -> advisor: returns the LARGEST scale meeting the overlap ceiling
         (largest-valid, never shrink-to-pass) + the full sweep table.

  border <candidate.png> [--strip-px 3] [--max-occupancy 0.02]
      -> fraction of the outer N-px border strip that is non-background;
         FAILs above --max-occupancy (never-crop-canvas-edges rule).

Calibration note (PROVISIONAL): the default --overlap-max 0.5 is derived only
from this session's accepted exemplars (measured 0.01-0.12% overlap on
marine-coral-panels). No rejected near-misses are in the corpus yet, so this
threshold is an advisor default, not a validated boundary — tighten/loosen it
once real near-miss data exists.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

DEFAULT_OVERLAP_MAX = 0.5  # PROVISIONAL — see module docstring calibration note


def load_spec(spec_path: str) -> dict:
    with open(spec_path) as f:
        return json.load(f)


def px(spec: dict, x: float) -> float:
    ab0 = spec["ab_x"][0]
    return (x - ab0) * spec["render_scale"]


def py(spec: dict, y: float) -> float:
    return (spec["ab_top"] - y) * spec["render_scale"]


def part_crop(spec: dict, part: str, render_path: str):
    l, t, r, b = spec["parts"][part]["cut_ltrb"]
    im = Image.open(render_path).convert("RGB")
    box = (int(px(spec, l)), int(py(spec, t)), int(px(spec, r)), int(py(spec, b)))
    return im.crop(box), box


def coral_mask(im: Image.Image, fg_thresh: int = 20) -> np.ndarray:
    """Foreground/painted-pixel mask for a candidate element image.

    If the image has real transparency, alpha>40 is foreground; otherwise
    fall back to luma<248 (non-white). fg_thresh is accepted for CLI symmetry
    with fish_mask's alpha threshold but the coral/luma logic is verbatim from
    overlay_tool.py.
    """
    im = im.convert("RGBA")
    a = np.array(im)
    alpha = a[:, :, 3]
    if alpha.min() < 250:  # has real transparency
        return alpha > 40
    luma = 0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]
    return luma < 248


def fish_mask(creature_alpha_path: str, box, safety_px: int = 6, fg_thresh: int = 20) -> np.ndarray:
    """Dilated creature/element silhouette mask cropped to `box` (part crop box)."""
    from scipy.ndimage import binary_dilation

    a = np.array(Image.open(creature_alpha_path).convert("RGBA"))[:, :, 3] > fg_thresh
    sub = a[box[1] : box[3], box[0] : box[2]]
    return binary_dilation(sub, iterations=safety_px)


def border_check(candidate_path: str, strip_px: int = 3, max_occupancy: float = 0.02) -> dict:
    """Fraction of the outer `strip_px` border that carries non-background pixels.

    FAILs above max_occupancy (never-crop-canvas-edges: subject must never be
    cut off at the canvas edge).
    """
    im = Image.open(candidate_path).convert("RGBA")
    a = np.array(im)
    h, w = a.shape[:2]
    fg = coral_mask(im)
    strip = np.zeros((h, w), bool)
    strip[:strip_px, :] = True
    strip[-strip_px:, :] = True
    strip[:, :strip_px] = True
    strip[:, -strip_px:] = True
    strip_px_total = int(strip.sum())
    occ_px = int((strip & fg).sum())
    occupancy = occ_px / max(1, strip_px_total)
    return {
        "border_strip_px": strip_px,
        "border_occupancy": round(occupancy, 4),
        "border_max_occupancy": max_occupancy,
        "border_pass": occupancy <= max_occupancy,
    }


def check(
    spec: dict,
    part: str,
    render_path: str,
    creature_alpha_path: str,
    candidate_path: str,
    scale: float = 1.0,
    xoff: float = 0.0,
    safety_px: int = 6,
    fg_thresh: int = 20,
    overlap_max: float = DEFAULT_OVERLAP_MAX,
    overlay_out: str | None = None,
    strip_px: int = 3,
    max_occupancy: float = 0.02,
) -> dict:
    crop, box = part_crop(spec, part, render_path)
    cw, ch = crop.size

    candidate = Image.open(candidate_path)
    m = coral_mask(candidate, fg_thresh)
    ci = Image.fromarray((m * 255).astype("uint8"))
    tw = int(cw * scale)
    th = int(tw * candidate.height / candidate.width)
    ci = ci.resize((tw, th))
    cm = np.array(ci) > 128

    canvas = np.zeros((ch, cw), bool)
    x0 = int((cw - tw) / 2 + xoff * cw)
    hh = min(th, ch)
    xs = max(0, x0)
    xe = min(cw, x0 + tw)
    csx = xs - x0
    canvas[ch - hh : ch, xs:xe] = cm[th - hh : th, csx : csx + (xe - xs)]

    band_px = int(canvas.sum())
    creature = fish_mask(creature_alpha_path, box, safety_px, fg_thresh)
    creature = creature[:ch, :cw] if creature.shape != (ch, cw) else creature
    overlap = int((canvas & creature).sum())
    overlap_pct = round(100 * overlap / max(1, band_px), 4)

    floor_y = None
    P = spec["parts"][part]
    if "fish_floor_y" in P:
        floor_y = int(py(spec, P["fish_floor_y"]) - box[1])
    above_floor_pct = None
    if floor_y is not None:
        above_floor = int(canvas[: max(0, floor_y), :].sum())
        above_floor_pct = round(100 * above_floor / max(1, band_px), 4)

    res = {
        "part": part,
        "scale": scale,
        "xoff": xoff,
        "band_px": band_px,
        "creature_overlap_px": overlap,
        "overlap_pct": overlap_pct,
        "overlap_max": overlap_max,
        "above_floor_pct": above_floor_pct,
        "pass": overlap_pct <= overlap_max,
    }
    res.update(border_check(candidate_path, strip_px, max_occupancy))
    res["pass"] = res["pass"] and res["border_pass"]

    if overlay_out:
        vis = crop.convert("RGBA")
        ov = np.zeros((ch, cw, 4), "uint8")
        ov[canvas] = [255, 120, 0, 110]
        ov[canvas & creature] = [255, 0, 0, 220]
        Image.alpha_composite(vis, Image.fromarray(ov, "RGBA")).convert("RGB").save(overlay_out)

    return res


def search(
    spec: dict,
    part: str,
    render_path: str,
    creature_alpha_path: str,
    candidate_path: str,
    overlap_max: float,
    scale_range: str,
    xoff: float = 0.0,
    safety_px: int = 6,
    fg_thresh: int = 20,
) -> dict:
    lo, hi, step = (float(v) for v in scale_range.split(":"))
    sweep = []
    scale = lo
    best = None
    n = 0
    while scale <= hi + 1e-9 and n < 10000:
        n += 1
        res = check(
            spec, part, render_path, creature_alpha_path, candidate_path,
            scale=round(scale, 6), xoff=xoff, safety_px=safety_px, fg_thresh=fg_thresh,
            overlap_max=overlap_max,
        )
        sweep.append(res)
        if res["pass"] and (best is None or res["scale"] > best["scale"]):
            best = res
        scale += step
    return {"best": best, "sweep": sweep}


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add_common(p):
        p.add_argument("--panel-spec", required=True, help="geometry_spec.json path")
        p.add_argument("--render", required=True, help="rendered part sheet PNG (RENDER)")
        p.add_argument("--creature-alpha", required=True, help="creature/element silhouette PNG (PRINT)")
        p.add_argument("--safety-px", type=int, default=6, help="dilation safety margin, px (default 6)")
        p.add_argument("--fg-thresh", type=int, default=20, help="alpha threshold for creature fg (default 20)")
        p.add_argument("--strip-px", type=int, default=3, help="border strip width, px (default 3)")
        p.add_argument("--max-occupancy", type=float, default=0.02, help="border FAIL ceiling (default 0.02 = 2%%)")

    p_check = sub.add_parser("check", help="measure one candidate at one scale")
    p_check.add_argument("part")
    p_check.add_argument("candidate")
    add_common(p_check)
    p_check.add_argument("--scale", type=float, default=1.0)
    p_check.add_argument("--xoff", type=float, default=0.0)
    p_check.add_argument("--overlap-max", type=float, default=DEFAULT_OVERLAP_MAX,
                          help=f"overlap%% FAIL ceiling (default {DEFAULT_OVERLAP_MAX}, PROVISIONAL calibration — "
                               "see module docstring)")
    p_check.add_argument("--overlay-out", default=None)

    p_search = sub.add_parser("search", help="sweep scale, return largest scale meeting the ceiling")
    p_search.add_argument("part")
    p_search.add_argument("candidate")
    add_common(p_search)
    p_search.add_argument("--overlap-max", type=float, default=DEFAULT_OVERLAP_MAX)
    p_search.add_argument("--scale-range", required=True, help="LO:HI:STEP e.g. 0.6:1.2:0.05")
    p_search.add_argument("--xoff", type=float, default=0.0)

    p_border = sub.add_parser("border", help="border/no-crop check only")
    p_border.add_argument("candidate")
    p_border.add_argument("--strip-px", type=int, default=3)
    p_border.add_argument("--max-occupancy", type=float, default=0.02)

    return ap


def main(argv=None) -> int:
    ap = _build_parser()
    args = ap.parse_args(argv)

    if args.cmd == "border":
        res = border_check(args.candidate, args.strip_px, args.max_occupancy)
        print(json.dumps(res))
        return 0 if res["border_pass"] else 1

    spec = load_spec(args.panel_spec)
    if args.part not in spec["parts"]:
        print(f"unknown part {args.part!r}; spec parts: {list(spec['parts'].keys())}", file=sys.stderr)
        return 2

    if args.cmd == "check":
        overlay_out = args.overlay_out
        res = check(
            spec, args.part, args.render, args.creature_alpha, args.candidate,
            scale=args.scale, xoff=args.xoff, safety_px=args.safety_px, fg_thresh=args.fg_thresh,
            overlap_max=args.overlap_max, overlay_out=overlay_out,
            strip_px=args.strip_px, max_occupancy=args.max_occupancy,
        )
        print(json.dumps(res))
        return 0 if res["pass"] else 1

    if args.cmd == "search":
        res = search(
            spec, args.part, args.render, args.creature_alpha, args.candidate,
            overlap_max=args.overlap_max, scale_range=args.scale_range, xoff=args.xoff,
            safety_px=args.safety_px, fg_thresh=args.fg_thresh,
        )
        print(json.dumps(res))
        return 0 if res["best"] is not None else 1

    return 2


if __name__ == "__main__":
    sys.exit(main())
