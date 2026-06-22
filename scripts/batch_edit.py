#!/usr/bin/env python3
"""batch_edit.py — apply MANY element edits to ONE illustration in a single run.

Our real tasks are multi-element ("fix the 3 taxis", "fix the 5 fairies"): you
want to remove/redraw several elements of the SAME image and end with ONE final
artifact carrying every change. This driver does exactly that.

WHY SEQUENTIAL (do NOT parallelize the composites)
---------------------------------------------------
Every edit composites onto the SAME canvas. Job N must see the result of jobs
1..N-1 — otherwise two parallel composites onto the original would each be blind
to the other's change and the last writer would clobber the first (you'd lose an
edit). So we ACCUMULATE: job 1 edits --src -> step_1.png; job 2 edits step_1.png
-> step_2.png; ... ; the last step is the final image. This mirrors how we chained
the 3 taxis by hand. (Generation/search fan-out can be parallel — see falbatch.py
— but a stack of edits on one shared canvas is inherently serial.)

Each job reuses scripts/edit.py (we do NOT reimplement the automask -> engine ->
diff-mask composite -> pixel-gate -> judge pipeline): edit.py already does one
element correctly and emits a `<out>.json` provenance sidecar + an exit code
(0=SUCCESS, 2=NEEDS-REVIEW). We just chain it and aggregate.

JOBS FILE (JSON list); each job is an object:
    {
      "op": "remove" | "redraw",     # required: passed to edit.py --op
      "element": "the small taxi",   # required: edit.py --element (what to find)
      "box": "x0,y0,x1,y1",          # optional but recommended: which instance
      "desc": "a clean yellow sedan",# required for redraw: edit.py --desc
      "out_suffix": "taxi_right",    # required: names the per-step output / row
      "free": true                   # optional: edit.py --free (local LaMa eraser)
    }

OUTPUTS (under --outdir, default tasks/improve/):
  <final>                         the one accumulated image with EVERY change
  <stem>.batch.json               combined provenance (src, per-job results, the
                                  step chain, and each job's edit.py sidecar)
  + a printed summary table (per element: op, pixel gate, judge, RESULT).

CLI:
    .venv-gen/bin/python scripts/batch_edit.py --src IMG --jobs jobs.json --final OUT.png
  (any interpreter works — edit.py is invoked with this same interpreter; fal
  calls inside edit.py use its own venvs.)
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image

R = Path(__file__).resolve().parent          # scripts/
ROOT = R.parent                              # repo root
PY = sys.executable
EDIT = R / "edit.py"


def run_edit(src: Path, job: dict, out: Path) -> dict:
    """Run scripts/edit.py for ONE job against `src`, writing to `out`.

    Returns a result dict: the parsed edit.py provenance sidecar (if written)
    plus the subprocess exit code and a compact row for the summary table.
    edit.py exits 0=SUCCESS, 2=NEEDS-REVIEW; either way it writes <out>.json.
    """
    op = job["op"]
    element = job["element"]
    cmd = [PY, str(EDIT), "--src", str(src), "--op", op,
           "--element", element, "--out", str(out)]
    if op == "redraw":
        cmd += ["--desc", job.get("desc", "a clean version")]
    if job.get("box"):
        cmd += ["--box", str(job["box"])]
    if job.get("free"):
        cmd += ["--free"]
    # extra passthrough knobs if the job sets them
    for k, flag in (("ctx_pad", "--ctx-pad"), ("mask_dilate", "--mask-dilate"),
                    ("seed", "--seed")):
        if k in job:
            cmd += [flag, str(job[k])]

    print(f"\n[batch_edit] $ {' '.join(cmd)}")
    p = subprocess.run(cmd, capture_output=True, text=True)
    # stream edit.py output through so the run is auditable
    if p.stdout:
        sys.stdout.write(p.stdout)
    if p.stderr:
        sys.stderr.write(p.stderr)

    sidecar = Path(str(out) + ".json")
    prov = {}
    if sidecar.exists():
        try:
            prov = json.loads(sidecar.read_text())
        except Exception:
            prov = {"_sidecar_parse_error": True}

    applied = out.exists()
    # RESULT: prefer edit.py's own verdict; exit 0 == SUCCESS.
    result = prov.get("result")
    if result is None:
        result = "SUCCESS" if p.returncode == 0 else "NEEDS-REVIEW"
    judge = prov.get("judge", {}) or {}
    return {
        "out_suffix": job.get("out_suffix"),
        "op": op,
        "element": element,
        "box": job.get("box"),
        "out": str(out),
        "exit_code": p.returncode,
        "applied": applied,
        "pixel_gate_ok": prov.get("pixel_gate_ok"),
        "judge_verdict": judge.get("verdict"),
        "judge_leftover_text": judge.get("leftover_text"),
        "result": result,
        "provenance": prov,
    }


def run_parallel(src: Path, jobs: list[dict], work: Path, max_workers: int):
    """OPT-IN fast path for NON-OVERLAPPING multi-element edits.

    Runs edit.py concurrently per job — each against the ORIGINAL src (not an accumulating
    canvas) — so the N fal gens overlap (wall ~= slowest, not sum). This is only correct when
    the elements don't touch: edit.py guarantees the output equals src byte-exact OUTSIDE its
    element (diffmask + outside_max_delta=0), so each output differs from src only in its own
    region. We then MERGE by diff: final = src, overlaid with each output's changed pixels.
    If two jobs' changed regions intersect we cannot safely merge in parallel (each gen was
    blind to the other) -> hard error telling the caller to use the sequential default.

    Returns (rows, final_image). The overlap test is MEASURED (diff intersection), not a box guess.
    """
    src_arr = np.asarray(Image.open(src).convert("RGB")).astype(np.int16)

    def one(idx_job):
        i, job = idx_job
        suffix = job.get("out_suffix") or f"job{i}"
        step_out = work / f"par_{i}_{suffix}.png"
        print(f"[batch_edit//] dispatch job {i}/{len(jobs)}: {job['op']} '{job['element']}' -> {step_out.name}")
        r = run_edit(src, job, step_out)      # each job edits the ORIGINAL src, in its own process
        return i, job, r, step_out

    with ThreadPoolExecutor(max_workers=min(len(jobs), max_workers)) as ex:
        results = sorted(ex.map(one, list(enumerate(jobs, 1))), key=lambda t: t[0])

    final_arr = src_arr.copy()
    union = np.zeros(src_arr.shape[:2], bool)   # pixels already claimed by a prior job
    rows = []
    for i, job, r, step_out in results:
        rows.append(r)
        if not r["applied"]:
            print(f"[batch_edit//] WARN job {i} produced no output; skipped in merge")
            continue
        out_arr = np.asarray(Image.open(step_out).convert("RGB")).astype(np.int16)
        if out_arr.shape != src_arr.shape:
            raise SystemExit(f"[batch_edit//] job {i} output {out_arr.shape} != src {src_arr.shape}; "
                             "edit.py must not resize. Use the sequential default for this set.")
        diff = np.abs(out_arr - src_arr).sum(2) > 8      # where this job actually changed src
        inter = int((diff & union).sum())
        if inter > 0:
            raise SystemExit(
                f"[batch_edit//] job {i} ('{job['element']}') OVERLAPS an earlier job's changed "
                f"region by {inter}px — parallel merge would lose an edit. Re-run WITHOUT --parallel "
                "(the sequential default accumulates onto one canvas and handles overlap correctly).")
        union |= diff
        final_arr[diff] = out_arr[diff]
    return rows, Image.fromarray(final_arr.astype("uint8"))


def print_summary(rows: list[dict], final: Path):
    print("\n" + "=" * 78)
    print("[batch_edit] SUMMARY")
    print("=" * 78)
    hdr = f"{'#':<3}{'element':<26}{'op':<8}{'pixgate':<9}{'judge':<10}{'RESULT':<14}"
    print(hdr)
    print("-" * 78)
    for i, r in enumerate(rows, 1):
        elem = (r["element"] or "")[:25]
        pg = ("OK" if r["pixel_gate_ok"] else "FAIL") if r["pixel_gate_ok"] is not None else "?"
        jv = str(r["judge_verdict"] or "-")[:9]
        print(f"{i:<3}{elem:<26}{r['op']:<8}{pg:<9}{jv:<10}{r['result']:<14}")
    print("-" * 78)
    n_ok = sum(1 for r in rows if r["result"] == "SUCCESS")
    print(f"jobs: {len(rows)}  SUCCESS: {n_ok}  NEEDS-REVIEW: {len(rows) - n_ok}")
    print(f"final image -> {final}")


def main():
    ap = argparse.ArgumentParser(description="Apply many element edits to one image, sequentially.")
    ap.add_argument("--src", required=True, help="the ONE source illustration")
    ap.add_argument("--jobs", required=True, help="JSON list of jobs (op/element/box/desc/out_suffix)")
    ap.add_argument("--final", help="final accumulated image path (default: <outdir>/<srcstem>_batch_final.png)")
    ap.add_argument("--outdir", default="tasks/improve", help="dir for the final image + provenance")
    ap.add_argument("--parallel", action="store_true",
                    help="OPT-IN: run jobs concurrently against the ORIGINAL src + diff-merge "
                         "(fast for NON-OVERLAPPING elements; errors if changed regions intersect). "
                         "Default is the verified sequential accumulation.")
    ap.add_argument("--max-workers", type=int, default=6, help="max concurrent edit.py processes when --parallel")
    a = ap.parse_args()

    src = Path(a.src).resolve()
    if not src.exists():
        raise SystemExit(f"[batch_edit] src not found: {src}")

    jobs_path = Path(a.jobs)
    if not jobs_path.is_absolute():
        jobs_path = (ROOT / jobs_path)
    jobs = json.loads(jobs_path.read_text())
    if not isinstance(jobs, list) or not jobs:
        raise SystemExit("[batch_edit] jobs file must be a non-empty JSON list")

    outdir = Path(a.outdir)
    if not outdir.is_absolute():
        outdir = ROOT / outdir
    outdir.mkdir(parents=True, exist_ok=True)
    final = Path(a.final).resolve() if a.final else (outdir / f"{src.stem}_batch_final.png")
    final.parent.mkdir(parents=True, exist_ok=True)

    work = Path(tempfile.mkdtemp(prefix="batch_edit_"))
    print(f"[batch_edit] {len(jobs)} job(s) on {src.name}  final={final}  work={work}")
    if a.parallel and len(jobs) > 1:
        print("[batch_edit] PARALLEL mode: jobs run concurrently vs the ORIGINAL src, then diff-merge "
              "(NON-OVERLAPPING elements only; errors on intersecting changes).")
        rows, final_img = run_parallel(src, jobs, work, a.max_workers)
        final_img.save(final)
        chain = [str(src), str(final)]
    else:
        print("[batch_edit] SEQUENTIAL accumulation: each edit composites onto the previous result.")
        rows = []
        chain = [str(src)]
        cur = src  # accumulating image; starts at the source
        for i, job in enumerate(jobs, 1):
            suffix = job.get("out_suffix") or f"job{i}"
            step_out = work / f"step_{i}_{suffix}.png"
            print(f"\n[batch_edit] --- job {i}/{len(jobs)}: {job['op']} '{job['element']}' "
                  f"(suffix={suffix}) ---")
            r = run_edit(cur, job, step_out)
            rows.append(r)
            if r["applied"]:
                # accumulate: next job edits THIS result (sequential stacking)
                cur = step_out
                chain.append(str(step_out))
            else:
                print(f"[batch_edit] WARN job {i} produced no output; keeping prior canvas "
                      f"({cur}) for the next job")
        # the last successfully-applied step is the final image
        shutil.copy(cur, final)
        # carry the final overlay next to it if edit.py made one for the last step
        last_ov = Path(str(cur).replace(".png", "_editov.png"))
        if last_ov.exists():
            shutil.copy(last_ov, final.with_name(final.stem + "_editov.png"))

    combined = {
        "src": str(src),
        "final": str(final),
        "n_jobs": len(jobs),
        "step_chain": chain,
        "jobs": rows,
        "n_success": sum(1 for r in rows if r["result"] == "SUCCESS"),
        "mode": "parallel" if (a.parallel and len(jobs) > 1) else "sequential",
        "note": ("PARALLEL: each job edited the ORIGINAL src concurrently; the final is a diff-merge "
                 "of their disjoint changed regions (overlap is rejected)."
                 if (a.parallel and len(jobs) > 1) else
                 "Edits applied SEQUENTIALLY onto an accumulating canvas (each composites onto the "
                 "previous result). Composites are NOT parallelized — they share the canvas, so order matters."),
    }
    prov_path = final.with_suffix(".batch.json")
    prov_path.write_text(json.dumps(combined, indent=2))

    print_summary(rows, final)
    print(f"[batch_edit] combined provenance -> {prov_path}")

    all_ok = all(r["result"] == "SUCCESS" for r in rows) and all(r["applied"] for r in rows)
    raise SystemExit(0 if all_ok else 2)


if __name__ == "__main__":
    main()
