#!/usr/bin/env python3
"""ONE command to FIT artwork to a die-cut SVG (skyline / door use case).

Thin wrapper over the verified geometry route. It does NOT reimplement generation
or measurement — it resolves the requested panel to a --bbox, then chains the two
existing scripts and prints a single PASS/FAIL verdict:

  1. scripts/controlnet_sdxl_gen.py  -> paints artwork into the panel BODY only
     (SDXL-inpaint + xinsir canny ControlNet on the SVG lineart; openings/holes are
     masked out + composited to white, so region-IoU lands ~1.0 "by construction").
  2. scripts/measure_sdxl_cn.py      -> MEASURES the output against the SAME bbox
     masks (region-IoU, coverage, holes-clear) and writes an overlay.

Panels are the canonical skyline 3-panel convention from skyline_panel.PANELS:
  center -> the door/center outer_contour panel
  left / right -> the narrow side paintable panels
  auto -> the single largest body in the SVG (the center door for the skyline file)

Usage:
  fit.py --svg PATH --prompt "..." [--panel center|left|right|auto] [--out OUT.png]
         [--width 1024] [--steps N] [--seed N] [--iou-pass 0.9] [--python EXE]

The heavy generation step needs the diffusers stack — run with the project's
.venv-gen interpreter, e.g.:
  .venv-gen/bin/python scripts/fit.py --svg "assets/skyline/city-skyline template.svg" \
      --panel center --prompt "a watercolor-and-ink city brownstone facade"

Exit code: 0 on PASS, 1 on FAIL (or on a sub-step error).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import skyline_panel as S  # noqa: E402  (authoritative panel convention)

# CLI panel name -> skyline_panel.PANELS key. "center" is the door/center panel.
PANEL_ALIAS = {"center": "door", "door": "door", "left": "left", "right": "right"}


def resolve_bbox(svg: Path, panel: str):
    """Return (panel_key, (L, T, R, B)) in SVG user units for the requested panel.

    Reuses skyline_panel.panel_bbox so the crop matches the rest of the skyline
    tooling exactly. 'auto' picks the single largest body (the center door here).
    """
    vb, cl = S.load(str(svg))
    if panel == "auto":
        bodies = [s for s in cl if s.polygon is not None
                  and s.role in ("outer_contour", "paintable_region")]
        if not bodies:
            raise SystemExit(f"fit: no body/contour shapes found in {svg}")
        biggest = max(bodies, key=lambda s: s.area)
        return "auto", tuple(round(v, 2) for v in biggest.bounds)
    key = PANEL_ALIAS.get(panel)
    if key is None:
        raise SystemExit(f"fit: unknown --panel '{panel}' (use center|left|right|auto)")
    bbox, _poly = S.panel_bbox(cl, key)
    return key, tuple(round(v, 2) for v in bbox)


def run(cmd: list[str]) -> int:
    print(f"[fit] $ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd).returncode


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--svg", required=True, type=Path)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--panel", default="auto",
                    choices=["center", "left", "right", "door", "auto"])
    ap.add_argument("--out", type=Path, help="output PNG (default tasks/improve/_fit_<panel>.png)")
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--negative-prompt", default=None,
                    help="override gen negative prompt (default = gen script's)")
    ap.add_argument("--iou-pass", type=float, default=0.90,
                    help="min region-IoU to PASS (default 0.90)")
    ap.add_argument("--opening-pass", type=float, default=0.85,
                    help="min opening_fill to PASS under full-bleed (default 0.85). "
                         "Catches the door taper that region-IoU is blind to.")
    ap.add_argument("--corner-pass", type=float, default=0.75,
                    help="min worst bottom-corner fill to PASS under full-bleed (default 0.75)")
    ap.add_argument("--full-bleed", dest="full_bleed", action="store_true", default=None,
                    help="force full-bleed facade fit (no flap taper). Auto-on for the "
                         "door/center panel; this overrides the auto-detection.")
    ap.add_argument("--no-full-bleed", dest="full_bleed", action="store_false",
                    help="force the legacy flap-carving behaviour even on the door panel")
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter for the sub-steps (default: this one)")
    ap.add_argument("--smoke", action="store_true",
                    help="fast memory smoke run (tiny res, 2 steps); NOT a real fit")
    a = ap.parse_args()

    svg = a.svg if a.svg.is_absolute() else ROOT / a.svg
    if not svg.exists():
        print(f"fit: SVG not found: {svg}")
        return 1

    panel_key, bbox = resolve_bbox(svg, a.panel)
    L, T, R, B = bbox
    bbox_str = f"{L},{T},{R},{B}"

    # The door/center panel is a FULL-BLEED facade scene: it must paint edge-to-edge
    # inside the rectangular contour. Without full-bleed the large saloon-flap cutouts
    # get carved from the paint mask + drawn bold in the control map, and the model
    # tapers the facade to a trapezoid (white bottom corners). Auto-on for door/center
    # unless the user overrides with --full-bleed / --no-full-bleed.
    full_bleed = a.full_bleed if a.full_bleed is not None else (panel_key == "door")

    out = a.out if a.out else ROOT / f"tasks/improve/_fit_{a.panel}.png"
    out = out if out.is_absolute() else ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    overlay = out.with_name(out.stem + "_overlay.png")
    metrics = out.with_name(out.stem + "_metrics.json")

    print(f"[fit] svg={svg.name} panel={a.panel}->{panel_key} "
          f"bbox=({L},{T},{R},{B}) aspect={(R-L)/(B-T):.3f} full_bleed={full_bleed}", flush=True)

    # ---- step 1: generate (the verified geometry route) --------------------
    t0 = time.time()
    gen = [a.python, str(ROOT / "scripts/controlnet_sdxl_gen.py"),
           "--svg", str(svg), "--out", str(out),
           "--bbox", bbox_str, "--prompt", a.prompt,
           "--width", str(a.width), "--steps", str(a.steps), "--seed", str(a.seed)]
    if a.negative_prompt is not None:
        gen += ["--negative-prompt", a.negative_prompt]
    if full_bleed:
        gen += ["--full-bleed"]
    if a.smoke:
        gen += ["--smoke"]
    rc = run(gen)
    if rc != 0 or not out.exists():
        print(f"\n=== FIT: FAIL ===\ngeneration step failed (rc={rc}); no output at {out}")
        return 1

    # ---- step 2: measure geometry (the gate) -------------------------------
    meas = [a.python, str(ROOT / "scripts/measure_sdxl_cn.py"), str(out),
            "--svg", str(svg), "--bbox", bbox_str,
            "--out-overlay", str(overlay), "--json-out", str(metrics)]
    if full_bleed:
        meas += ["--full-bleed"]
    rc = run(meas)
    if rc != 0 or not metrics.exists():
        print(f"\n=== FIT: FAIL ===\nmeasurement step failed (rc={rc})")
        return 1

    m = json.loads(metrics.read_text())
    iou = m.get("region_iou", 0.0)
    holes_clear = bool(m.get("holes_clear", False))
    coverage = m.get("coverage", 0.0)
    opening_fill = m.get("opening_fill", 0.0)
    worst_corner = m.get("worst_corner_fill", 1.0)
    outside = m.get("outside_frac", 0.0)
    n_holes = m.get("n_holes", 0)
    n_clear = m.get("n_holes_clear", 0)

    # GATE: region-IoU + holes-clear always. Under full-bleed, ALSO require opening_fill
    # and worst bottom-corner fill so a tapered trapezoid (region-IoU 1.0 but white
    # corners) FAILS — the bug region-IoU alone is blind to.
    passed = (iou >= a.iou_pass) and holes_clear
    if full_bleed:
        passed = passed and (opening_fill >= a.opening_pass) and (worst_corner >= a.corner_pass)
    verdict = "PASS" if passed else "FAIL"
    dt = time.time() - t0

    print("\n" + "=" * 56)
    print(f"=== FIT: {verdict} ===  ({dt:.0f}s, {a.steps} steps @ {a.width}px)")
    print(f"  panel        : {a.panel} -> {panel_key}  bbox={bbox_str}  full_bleed={full_bleed}")
    print(f"  region-IoU   : {iou:.4f}   (PASS >= {a.iou_pass})")
    print(f"  holes-clear  : {holes_clear}   ({n_clear}/{n_holes} cutouts clear)")
    print(f"  coverage     : {coverage:.4f}   outside_frac: {outside:.4f}")
    if full_bleed:
        print(f"  opening_fill : {opening_fill:.4f}   (PASS >= {a.opening_pass})")
        print(f"  worst_corner : {worst_corner:.4f}   (PASS >= {a.corner_pass})")
    print(f"  output       : {out}")
    print(f"  overlay      : {overlay}")
    print(f"  metrics      : {metrics}")
    print("=" * 56)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
