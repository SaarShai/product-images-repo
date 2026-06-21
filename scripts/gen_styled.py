#!/usr/bin/env python3
"""gen_styled.py — reference-locked redraw/restyle that AUTO-FEEDS style refs.

LAW 0 (reference beats prose): to redraw an element so it matches the surrounding
art, you must drive the generator with ACTUAL in-style reference crops of the same
illustration, not a worded description. This script makes that automatic:

  1. Calls scripts/style_packet.py to auto-extract N in-style reference crops from
     the SAME source illustration, EXCLUDING the element's own box (--avoid) so the
     refs sample the surrounding art, never the thing being redrawn.
  2. Calls scripts/falref_apply.py (fal Flux.2-pro edit) with
       image_urls = [ region_to_edit, *style_refs ]
     so the redrawn element matches the surrounding art style.

This script ORCHESTRATES the two existing scripts; it does not reimplement crop
extraction or the fal call.

CLI
---
python3 scripts/gen_styled.py --src IMG --crop x0,y0,x1,y1 \
    --element "the yellow taxi" --desc "a clean classic NYC yellow sedan" \
    --out OUT.png [--n-refs 3] [--avoid x0,y0,x1,y1 ...] [--refs-dir DIR]

If no explicit --avoid box is given, the element's own --crop is used as the
avoid box (so refs are pulled from everything EXCEPT the element).

Degrades gracefully: if the gen venv / fal key is missing the refs are still
built and the exact ref+prompt plan is reported, so the failure is actionable.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLE_PACKET = ROOT / "scripts" / "style_packet.py"
FALREF_APPLY = ROOT / "scripts" / "falref_apply.py"


def eprint(*a, **k):
    print(*a, file=sys.stderr, **k)


def parse_box(s: str):
    parts = [int(round(float(x))) for x in s.replace(" ", "").split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"box must be x0,y0,x1,y1 (got {s!r})")
    x0, y0, x1, y1 = parts
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def run(cmd, label):
    """Run a subprocess, stream its output, return (rc, stdout, stderr)."""
    eprint(f"[gen_styled] $ {' '.join(str(c) for c in cmd)}")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        eprint(f"[gen_styled] {label}: TIMEOUT")
        return 124, "", "timeout"
    except FileNotFoundError as e:
        eprint(f"[gen_styled] {label}: NOT FOUND ({e})")
        return 127, "", str(e)
    if p.stdout:
        eprint(p.stdout.rstrip())
    if p.stderr:
        eprint(p.stderr.rstrip())
    return p.returncode, p.stdout, p.stderr


def pick_python():
    """Prefer the gen venv (Pillow/numpy/requests) if present, else current python."""
    cand = ROOT / ".venv-gen" / "bin" / "python"
    if cand.exists():
        return str(cand)
    return sys.executable


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--src", required=True, help="source illustration")
    ap.add_argument("--crop", required=True, type=parse_box,
                    help="element box to redraw: x0,y0,x1,y1")
    ap.add_argument("--element", required=True,
                    help="what is being redrawn, e.g. 'the yellow taxi'")
    ap.add_argument("--desc", required=True,
                    help="short description of the desired redraw")
    ap.add_argument("--out", required=True, help="output redrawn region path")
    ap.add_argument("--n-refs", type=int, default=3, help="number of style refs")
    ap.add_argument("--avoid", type=parse_box, nargs="*", default=None,
                    help="keep-clear boxes for ref extraction; defaults to --crop")
    ap.add_argument("--refs-dir", default=None,
                    help="dir for extracted refs (default: <out>_refs/)")
    args = ap.parse_args(argv)

    src = Path(args.src)
    if not src.exists():
        eprint(f"[gen_styled] ERROR: src not found: {src}")
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    refs_dir = Path(args.refs_dir) if args.refs_dir else out.with_name(out.stem + "_refs")
    refs_dir.mkdir(parents=True, exist_ok=True)

    # Avoid the element's own box by default so refs sample the SURROUNDING art.
    avoid = args.avoid if args.avoid else [tuple(args.crop)]
    n_refs = max(1, args.n_refs)
    py = pick_python()

    # ---- Step 1: auto-extract in-style reference crops -------------------
    sp_cmd = [py, str(STYLE_PACKET),
              "--image", str(src),
              "--out-dir", str(refs_dir),
              "--n", str(n_refs)]
    for b in avoid:
        sp_cmd += ["--avoid", f"{b[0]},{b[1]},{b[2]},{b[3]}"]
    rc, _, _ = run(sp_cmd, "style_packet")
    if rc != 0:
        eprint(f"[gen_styled] FAIL: style_packet rc={rc} — cannot build refs.")
        return 1

    refs = sorted(refs_dir.glob("crop_*.png"))
    if not refs:
        eprint(f"[gen_styled] FAIL: no reference crops produced in {refs_dir}")
        return 1
    refs = refs[:n_refs]
    eprint(f"[gen_styled] built {len(refs)} style refs: "
           + ", ".join(r.name for r in refs))

    # ---- Build the reference-driven prompt (style comes from the IMAGES) --
    x0, y0, x1, y1 = args.crop
    prompt = (
        f"Redraw {args.element} as {args.desc}. "
        f"Match the exact art style, palette, line quality, and texture of the "
        f"attached reference crops (they are from the SAME illustration). "
        f"Keep the same framing, scale, and placement; change only {args.element}. "
        f"Do not add a description-driven look — copy the painted style of the refs."
    )

    # ---- Step 2: reference-locked element edit via falref_apply ----------
    fa_cmd = [py, str(FALREF_APPLY),
              "--src", str(src),
              "--crop", f"{x0},{y0},{x1},{y1}",
              "--prompt", prompt,
              "--out", str(out)]
    for r in refs:
        fa_cmd += ["--ref", str(r)]
    rc, _, _ = run(fa_cmd, "falref_apply")
    if rc != 0:
        eprint(f"[gen_styled] DEGRADED: falref_apply rc={rc} "
               f"(gen venv / fal key likely missing). "
               f"Refs are ready in {refs_dir}; prompt + crop are valid above.")
        return 1

    if not out.exists():
        eprint(f"[gen_styled] FAIL: falref_apply returned 0 but {out} missing.")
        return 1

    print(f"[gen_styled] OK -> {out}  (element={args.element!r}, "
          f"refs={len(refs)}, src={src.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
