#!/usr/bin/env python3
"""Objective pre-human gate report — the deterministic INTEGRATOR.

Both reviewers called this the highest-ROI item: ONE deterministic report a human
reads BEFORE doing any subjective judging, so the expensive human eyeball only
ever lands on candidates that already clear the cheap, objective hard-gates.

It orchestrates the now-built sibling scripts (it shells out to them so each stays
the single source of truth for its own check) and emits ONE JSON report:

  1. GEOMETRY  -> scripts/geom_gate.py   (fill-inside-contour, cutout/keep-clear,
                  per-role hard gate). PASS/FAIL + the metrics, verbatim.
  2. ELEMENT COUNT -> scripts/dup_detect.py with the panel's fixed-element
                  template (if one exists). How many times the known element
                  (e.g. a wooden window) actually appears -> catches the stacked
                  DOUBLE that a VLM count gate missed.
  3. OUTPUT-SIZE CONTRACT -> compares the candidate's aspect ratio against the
                  SVG viewBox aspect (from scripts/svg_manifest.py) and flags a
                  mismatch. A gen that came back at the wrong shape is broken
                  before anyone looks at the art.
  4. JUDGE PACKET -> scripts/judge_tiles.py (if present): hi-DPI tiles +
                  whole-panel context image, so the human (or a downstream VLM
                  judge) sees mid-panel detail at native resolution instead of a
                  hallucination-inducing downsample.

objective_verdict = PASS  iff  geom == PASS  AND  size_ok  (deterministic checks).
The element count is ADVISORY (dup_detect is noisy): if `needs_vlm_count` is True
(advisory count != expected), run the VLM count-on-context to resolve duplicates
before accepting. `human_pick` is always "PENDING" — this report only gates.

CLI:
  python3 scripts/objective_gate_report.py --cand PNG --svg SVG \
      [--template PNG] [--expect-windows N] [--out report.json] \
      [--mask PNG] [--geom-thresh F] [--aspect-tol F] [--no-tiles] [--quiet]

Exit code: 0 if objective_verdict == PASS, 1 if FAIL, 2 on a setup error
(missing input) — so it can gate a shell pipeline / loop.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PY = sys.executable or "python3"


def _abs(p: Path) -> Path:
    return p if p.is_absolute() else (ROOT / p)


def _run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a sibling script; return (returncode, stdout, stderr)."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# 1. geometry hard-gate
# ---------------------------------------------------------------------------
def run_geom(cand: Path, svg: Path, mask: Path | None, thresh: float) -> dict:
    cmd = [PY, str(SCRIPTS / "geom_gate.py"),
           "--cand", str(cand), "--svg", str(svg), "--thresh", str(thresh)]
    if mask is not None:
        cmd += ["--mask", str(mask)]
    rc, out, err = _run(cmd)
    # geom_gate prints the JSON report on stdout and exits 0/1 by verdict.
    try:
        report = json.loads(out)
    except json.JSONDecodeError:
        return {"verdict": "ERROR", "error": (err.strip() or out.strip() or
                                              "geom_gate produced no JSON"),
                "returncode": rc}
    report["returncode"] = rc
    return report


# ---------------------------------------------------------------------------
# 2. element-count (duplicate detector)
# ---------------------------------------------------------------------------
def run_count(cand: Path, template: Path | None, expected: int | None) -> dict:
    """Return {count, available, ...}. count=None when no template is given."""
    if template is None:
        return {"available": False, "count": None,
                "note": "no fixed-element template supplied; count not checked"}
    cmd = [PY, str(SCRIPTS / "dup_detect.py"),
           "--cand", str(cand), "--template", str(template)]
    if expected is not None:
        cmd += ["--expected", str(expected)]
    rc, out, err = _run(cmd)
    m = re.search(r"^count=(\d+)", out, re.MULTILINE)
    if not m:
        return {"available": True, "count": None,
                "error": (err.strip() or out.strip() or
                          "dup_detect produced no count"),
                "returncode": rc}
    return {"available": True, "count": int(m.group(1)),
            "returncode": rc, "stdout_head": out.strip().splitlines()[:1]}


# ---------------------------------------------------------------------------
# 3. output-size contract (candidate aspect vs viewBox aspect)
# ---------------------------------------------------------------------------
def svg_aspect(svg: Path) -> tuple[float | None, dict]:
    """Get the SVG viewBox W/H aspect via svg_manifest.py."""
    cmd = [PY, str(SCRIPTS / "svg_manifest.py"), "--svg", str(svg)]
    rc, out, err = _run(cmd)
    try:
        man = json.loads(out)
        vb = man["viewBox"]
        w, h = float(vb["w"]), float(vb["h"])
        if h <= 0:
            return None, {"error": "viewBox height <= 0"}
        return w / h, {"viewBox": vb}
    except Exception:
        return None, {"error": (err.strip() or out.strip() or
                                "svg_manifest produced no parseable viewBox")}


def candidate_aspect(cand: Path) -> tuple[float | None, list[int] | None]:
    from PIL import Image

    with Image.open(cand) as im:
        w, h = im.size
    if h <= 0:
        return None, [w, h]
    return w / h, [w, h]


# ---------------------------------------------------------------------------
# 4. judge packet (hi-DPI tiles + context) — best-effort
# ---------------------------------------------------------------------------
def run_tiles(cand: Path, out_dir: Path) -> dict:
    script = SCRIPTS / "judge_tiles.py"
    if not script.exists():
        return {"available": False, "note": "judge_tiles.py not present"}
    cmd = [PY, str(script), "--candidate", str(cand), "--out", str(out_dir)]
    rc, out, err = _run(cmd)
    man_path = out_dir / "manifest.json"
    if rc != 0 or not man_path.exists():
        return {"available": True, "ok": False,
                "error": (err.strip() or out.strip() or "judge_tiles failed"),
                "returncode": rc}
    try:
        man = json.loads(man_path.read_text())
    except Exception:
        man = {}
    tiles = [str(out_dir / t["file"]) for t in man.get("tiles", [])]
    ctx = man.get("context")
    context = str(out_dir / ctx) if ctx else None
    return {"available": True, "ok": True, "dir": str(out_dir),
            "tiles": tiles, "context": context, "manifest": str(man_path)}


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cand", required=True, type=Path, help="candidate PNG")
    ap.add_argument("--svg", required=True, type=Path, help="panel SVG")
    ap.add_argument("--template", type=Path,
                    help="fixed-element template PNG (for the count check)")
    ap.add_argument("--expect-windows", type=int, default=None,
                    help="expected fixed-element count; default: derive from the SVG manifest")
    ap.add_argument("--mask", type=Path,
                    help="contour-mask PNG passed through to geom_gate (default: its own default)")
    ap.add_argument("--geom-thresh", type=float, default=0.82,
                    help="fill_inside_contour threshold for geom_gate (default 0.82)")
    ap.add_argument("--aspect-tol", type=float, default=0.12,
                    help="max relative aspect difference (|cand-svg|/svg) before size_ok=False (default 0.12)")
    ap.add_argument("--tiles-dir", type=Path,
                    help="where judge_tiles writes the packet (default: <cand dir>/_gate/<cand stem>)")
    ap.add_argument("--no-tiles", action="store_true", help="skip the judge_tiles packet")
    ap.add_argument("--out", type=Path, help="write the JSON report here")
    ap.add_argument("--quiet", action="store_true", help="do not print the report to stdout")
    a = ap.parse_args()

    cand = _abs(a.cand)
    svg = _abs(a.svg)
    template = _abs(a.template) if a.template else None
    mask = _abs(a.mask) if a.mask else None

    if not cand.exists():
        print(f"ERROR: candidate not found: {cand}", file=sys.stderr)
        return 2
    if not svg.exists():
        print(f"ERROR: svg not found: {svg}", file=sys.stderr)
        return 2
    if template is not None and not template.exists():
        print(f"ERROR: template not found: {template}", file=sys.stderr)
        return 2

    fails: list[str] = []

    # --- output-size contract (also yields the SVG aspect for the report) ----
    asp_svg, asp_svg_meta = svg_aspect(svg)
    asp_cand, cand_size = candidate_aspect(cand)
    if asp_svg is None:
        size_ok = False
        rel_diff = None
        fails.append(f"could not read SVG viewBox aspect: {asp_svg_meta.get('error')}")
    elif asp_cand is None:
        size_ok = False
        rel_diff = None
        fails.append(f"could not read candidate aspect (size={cand_size})")
    else:
        rel_diff = abs(asp_cand - asp_svg) / asp_svg
        size_ok = rel_diff <= a.aspect_tol
        if not size_ok:
            fails.append(
                f"output size mismatch: cand aspect {asp_cand:.4f} vs svg {asp_svg:.4f} "
                f"(rel diff {rel_diff:.3f} > tol {a.aspect_tol:.3f})")

    # --- expected element count: explicit flag, else from the manifest -------
    expected = a.expect_windows
    if expected is None and isinstance(asp_svg_meta, dict):
        # svg_aspect only carried viewBox; re-read the manifest count cheaply.
        rc, out, _ = _run([PY, str(SCRIPTS / "svg_manifest.py"), "--svg", str(svg)])
        try:
            expected = int(json.loads(out)["expected_element_counts"]["windows"])
        except Exception:
            expected = None

    # --- geometry hard-gate --------------------------------------------------
    geom = run_geom(cand, svg, mask, a.geom_thresh)
    geom_verdict = geom.get("verdict", "ERROR")
    if geom_verdict != "PASS":
        if geom_verdict == "ERROR":
            fails.append(f"geom_gate error: {geom.get('error')}")
        else:
            gf = geom.get("fails") or []
            fails.append("geometry FAIL: " + ("; ".join(gf) if gf else "see geom report"))

    # --- element count (ADVISORY -> VLM escalation) --------------------------
    # dup_detect (template-matching) is NOISY: a real element can score as low as a
    # false match (proven — a clean panel's window 0.436 vs another panel's false
    # arch 0.440; no clean threshold separates them). So the code count is ADVISORY.
    # When it disagrees with `expected`, FLAG for an authoritative VLM count-on-
    # context (the proven-reliable method) instead of hard-failing here.
    count_info = run_count(cand, template, expected)
    window_count = count_info.get("count")
    count_warnings: list[str] = []
    needs_vlm_count = False
    if template is None:
        count_warnings.append("element count NOT checked (no --template)")
        needs_vlm_count = True
    elif window_count is None:
        count_warnings.append(f"element count error: {count_info.get('error')}")
        needs_vlm_count = True
    elif expected is None:
        count_warnings.append("expected count unknown (pass --expect-windows or fix SVG)")
        needs_vlm_count = True
    elif window_count != expected:
        count_warnings.append(
            f"advisory count {window_count} != expected {expected} -> escalate to VLM count-on-context")
        needs_vlm_count = True

    # --- judge packet (best-effort; never gates) -----------------------------
    if a.no_tiles:
        tiles_info = {"available": False, "note": "skipped (--no-tiles)"}
    else:
        tiles_dir = _abs(a.tiles_dir) if a.tiles_dir else (cand.parent / "_gate" / cand.stem)
        tiles_info = run_tiles(cand, tiles_dir)

    # --- objective verdict ---------------------------------------------------
    # HARD gate = the DETERMINISTIC checks only (geometry + output-size). The element
    # count is advisory: a PASS here with needs_vlm_count=True means "geometry/size
    # are clean — now run the VLM count-on-context before accepting."
    objective_pass = (geom_verdict == "PASS" and size_ok)
    objective_verdict = "PASS" if objective_pass else "FAIL"

    report = {
        "candidate": str(cand),
        "svg": str(svg),
        "template": str(template) if template else None,
        "geom": {
            "verdict": geom_verdict,
            "fill_inside_contour": geom.get("fill_inside_contour"),
            "overflow_outside_contour": geom.get("overflow_outside_contour"),
            "edge_iou": geom.get("edge_iou"),
            "per_role": geom.get("per_role"),
            "fails": geom.get("fails"),
            "warnings": geom.get("warnings"),
        },
        "dup_advisory_count": window_count,
        "window_count": window_count,
        "expected_count": expected,
        "needs_vlm_count": needs_vlm_count,
        "count_warnings": count_warnings,
        "size_ok": size_ok,
        "aspect_cand": round(asp_cand, 4) if asp_cand is not None else None,
        "aspect_svg": round(asp_svg, 4) if asp_svg is not None else None,
        "aspect_rel_diff": round(rel_diff, 4) if rel_diff is not None else None,
        "candidate_size": cand_size,
        "tiles": tiles_info.get("tiles", []),
        "context": tiles_info.get("context"),
        "tiles_info": tiles_info,
        "objective_verdict": objective_verdict,
        "fails": fails,
        "human_pick": "PENDING",
    }

    text = json.dumps(report, indent=2)
    if not a.quiet:
        print(text)
    if a.out:
        op = _abs(a.out)
        op.parent.mkdir(parents=True, exist_ok=True)
        op.write_text(text + "\n")
        print(f"report -> {op}", file=sys.stderr)

    return 0 if objective_verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
