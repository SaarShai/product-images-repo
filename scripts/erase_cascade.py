#!/usr/bin/env python3
"""erase_cascade.py — COST-CASCADE object eraser: free first, paid only if needed.

Cost discipline: try the FREE local LaMa eraser first, gate its quality, and only
escalate to the PAID fal Bria eraser when the free result fails a gate.

Cascade
-------
  1. FREE   : .venv-iopaint/bin/python scripts/lama_erase.py  --image --mask --out
  2. GATE   : .venv-metric/bin/python scripts/leak_metric.py  (outside-mask leak)
              .venv-ocr/bin/python    scripts/text_gate.py    (leftover healed text)
              -> PASS  : keep the free result, done (0 paid calls).
              -> FAIL  : escalate.
  3. PAID   : scripts/falgen.py --mode eraser --image --mask --out  (fal Bria)
              re-run the same gates on the paid result and report.

The leak gate compares the erased output against the ORIGINAL outside the mask
(the erase must not disturb anything beyond the masked object). The text gate
checks the masked region for healed-back glyphs (engines sometimes repaint text).

Degrades: a missing sub-venv (iopaint/metric/ocr) or missing fal key is reported,
not fatal — the cascade records WHY a stage was skipped and continues / stops
with an actionable engine verdict. Retries are bounded (one attempt per engine).

CLI
---
python3 scripts/erase_cascade.py --image IMG --mask MASK --out OUT \
    [--region x0,y0,x1,y1] [--leak-thresh 0.06] [--no-paid]

--region : box (in image px) for the text gate; defaults to the mask's bbox.
--out    : final accepted result (free if it passes, else paid).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np  # only for the default text-gate region from the mask bbox

ROOT = Path(__file__).resolve().parent.parent
LAMA = ROOT / "scripts" / "lama_erase.py"
LEAK = ROOT / "scripts" / "leak_metric.py"
TEXT = ROOT / "scripts" / "text_gate.py"
FALGEN = ROOT / "scripts" / "falgen.py"

VENV_IOPAINT = ROOT / ".venv-iopaint" / "bin" / "python"
VENV_METRIC = ROOT / ".venv-metric" / "bin" / "python"
VENV_OCR = ROOT / ".venv-ocr" / "bin" / "python"


def eprint(*a, **k):
    print(*a, file=sys.stderr, **k)


def parse_region(s: str):
    parts = [int(round(float(x))) for x in s.replace(" ", "").split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(f"region must be x0,y0,x1,y1 (got {s!r})")
    x0, y0, x1, y1 = parts
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def run(cmd, timeout=600):
    """Run a subprocess; stream output; return (rc, stdout, stderr).

    rc=127 if the interpreter/script is missing (degrade signal)."""
    eprint(f"[cascade] $ {' '.join(str(c) for c in cmd)}")
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        eprint("[cascade]   TIMEOUT")
        return 124, "", "timeout"
    except FileNotFoundError as e:
        eprint(f"[cascade]   NOT FOUND ({e})")
        return 127, "", str(e)
    if p.stdout:
        eprint(p.stdout.rstrip())
    if p.stderr:
        eprint(p.stderr.rstrip())
    return p.returncode, p.stdout, p.stderr


def mask_bbox(mask_path):
    """Return (x0,y0,x1,y1) bbox of white(>127) pixels, or None."""
    try:
        from PIL import Image
        m = np.asarray(Image.open(mask_path).convert("L"))
        ys, xs = np.where(m > 127)
        if xs.size == 0:
            return None
        return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    except Exception as e:
        eprint(f"[cascade] mask bbox failed: {e}")
        return None


def gate(candidate, orig, mask, region, leak_thresh):
    """Run leak + text gates on `candidate`. Returns (passed, summary_str).

    A missing gate venv DEGRADES that gate to 'skipped' (not a hard fail), so a
    free result can still be accepted on the available evidence. A gate that runs
    and FAILS blocks acceptance."""
    leak_ok = text_ok = True
    notes = []

    # ---- leak gate (outside-mask perceptual change) ----
    if VENV_METRIC.exists():
        rc, _, _ = run([str(VENV_METRIC), str(LEAK),
                        "--orig", str(orig), "--edited", str(candidate),
                        "--mask", str(mask), "--thresh", str(leak_thresh),
                        "--no-dino"])
        if rc == 0:
            notes.append("leak=PASS")
        elif rc == 1:
            leak_ok = False
            notes.append("leak=FAIL")
        else:
            notes.append(f"leak=ERR(rc{rc},skipped)")
    else:
        notes.append("leak=skipped(no .venv-metric)")

    # ---- text gate (healed-back glyphs in the masked region) ----
    if VENV_OCR.exists():
        tcmd = [str(VENV_OCR), str(TEXT), "--image", str(candidate)]
        if region:
            tcmd += ["--region", f"{region[0]},{region[1]},{region[2]},{region[3]}"]
        rc, _, _ = run(tcmd)
        if rc == 0:
            notes.append("text=CLEAN")
        elif rc == 2:
            text_ok = False
            notes.append("text=LEFTOVER")
        else:
            notes.append(f"text=ERR(rc{rc},skipped)")
    else:
        notes.append("text=skipped(no .venv-ocr)")

    return (leak_ok and text_ok), ", ".join(notes)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--image", required=True, help="source image")
    ap.add_argument("--mask", required=True, help="white(255)=remove region")
    ap.add_argument("--out", required=True, help="final accepted result")
    ap.add_argument("--region", type=parse_region, default=None,
                    help="text-gate box x0,y0,x1,y1 (default: mask bbox)")
    ap.add_argument("--leak-thresh", type=float, default=0.06)
    ap.add_argument("--no-paid", action="store_true",
                    help="never escalate to the paid engine")
    args = ap.parse_args(argv)

    image = Path(args.image)
    mask = Path(args.mask)
    out = Path(args.out)
    if not image.exists():
        eprint(f"[cascade] ERROR: image not found: {image}"); return 2
    if not mask.exists():
        eprint(f"[cascade] ERROR: mask not found: {mask}"); return 2
    out.parent.mkdir(parents=True, exist_ok=True)

    region = args.region or mask_bbox(mask)
    if region:
        eprint(f"[cascade] text-gate region = {region}")

    chosen = None  # which engine produced the accepted output

    # ---- Stage 1: FREE local LaMa eraser ----
    free_out = out.with_name(out.stem + "_free" + out.suffix)
    if VENV_IOPAINT.exists():
        eprint("[cascade] STAGE 1: FREE local LaMa eraser")
        rc, _, _ = run([str(VENV_IOPAINT), str(LAMA),
                        "--image", str(image), "--mask", str(mask),
                        "--out", str(free_out)])
        if rc == 0 and free_out.exists():
            passed, summary = gate(free_out, image, mask, region, args.leak_thresh)
            eprint(f"[cascade] FREE gates: {summary} => {'PASS' if passed else 'FAIL'}")
            if passed:
                out.write_bytes(free_out.read_bytes())
                chosen = "free:lama"
        else:
            eprint(f"[cascade] FREE eraser failed (rc={rc}); will try paid.")
    else:
        eprint("[cascade] STAGE 1 SKIPPED: .venv-iopaint missing (free eraser unavailable)")

    # ---- Stage 2: PAID fal Bria eraser (only if free failed/unavailable) ----
    if chosen is None and not args.no_paid:
        eprint("[cascade] STAGE 2: PAID fal Bria eraser (escalation)")
        paid_out = out.with_name(out.stem + "_paid" + out.suffix)
        rc, _, _ = run([sys.executable, str(FALGEN),
                        "--mode", "eraser",
                        "--image", str(image), "--mask", str(mask),
                        "--out", str(paid_out)])
        if rc == 0 and paid_out.exists():
            passed, summary = gate(paid_out, image, mask, region, args.leak_thresh)
            eprint(f"[cascade] PAID gates: {summary} => {'PASS' if passed else 'FAIL'}")
            out.write_bytes(paid_out.read_bytes())
            chosen = "paid:bria-fal" + ("" if passed else "(gates-failed,best-effort)")
        else:
            eprint(f"[cascade] PAID eraser failed/unavailable (rc={rc}).")
    elif chosen is None and args.no_paid:
        eprint("[cascade] --no-paid: not escalating.")

    if chosen is None:
        print("[cascade] RESULT: FAIL — no engine produced an accepted erase.")
        print("[cascade] ENGINE: none")
        return 1

    print(f"[cascade] RESULT: OK -> {out}")
    print(f"[cascade] ENGINE: {chosen}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
