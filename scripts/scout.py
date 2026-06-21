#!/usr/bin/env python3
"""scout.py — SCOUT-then-FINAL: cheap low-res candidates -> judge-pick -> one full-res render.

Cuts cost/latency on a single masked redraw. Instead of rendering N full-res
candidates (you pay N x full cost and throw away N-1), scout:

  Step 1 (SCOUT): generate N CHEAP candidates in parallel — small --maxside
          (default 768), one varied --seed each — by calling scripts/falgen.py
          concurrently (one blocking sync call per candidate, run together in a
          thread pool so wall time ~= the slowest single call, not the sum).
          (falbatch.py's queue API needs fal_client; falgen needs only requests,
          so the concurrent-falgen path is the portable one and the task allows it.)

  Step 2 (PICK): dedup + pairwise VLM tournament via scripts/sweep.py, which
          shells out to scripts/judge.py. Parses sweep's "[sweep] WINNER: <path>"
          line to identify the winning candidate (hence its seed).

  Step 3 (FINAL): re-render ONLY the winner's settings (same prompt + seed) at
          full --final-maxside (default 1400).

This REUSES falgen / sweep / judge unchanged — it never reimplements generation
or judging. Output: the final image + a JSON log of candidates and the pick.

Usage:
  python3 scripts/scout.py \
      --image tasks/nyc-taxi/work/L2_ctx.png \
      --mask  tasks/nyc-taxi/work/cabmask_ctx.png \
      --op redraw --n 3 \
      --prompt "a clean classic NYC yellow sedan" \
      --out-prefix tasks/improve/_scout_left

Secrets (FAL_KEY / OPENAI_API_KEY) are read by the sub-scripts from .secrets/;
scout never reads or prints them.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

# falgen mode for each scout op. "redraw" == masked inpaint that changes nothing
# outside the mask == falgen's `fill` endpoint (Flux Pro Fill).
OP_TO_MODE = {"redraw": "fill"}

WINNER_RE = re.compile(r"\[sweep\]\s+WINNER:\s+(.+?)\s*$", re.MULTILINE)


def _interp_for(needs):
    """Pick a python that can import the modules in `needs` for a sub-script.

    Prefer the current interpreter, then /usr/bin/python3 (the repo's resident
    3.9 user env where requests/PIL/httpx live). If none can satisfy `needs`,
    fall back to `uv run --no-project --with <pkg>...` which pulls the cached
    wheels (near-instant) — used only for the optional imagehash dedup.
    Returns (argv_prefix:list, label:str).
    """
    candidates = [sys.executable, "/usr/bin/python3", "python3"]
    seen = set()
    probe = "import " + ", ".join(needs) if needs else "pass"
    for c in candidates:
        if not c or c in seen:
            continue
        seen.add(c)
        exe = shutil.which(c) or (c if Path(c).exists() else None)
        if not exe:
            continue
        r = subprocess.run([exe, "-c", probe], capture_output=True, text=True)
        if r.returncode == 0:
            return [exe], exe
    # uv fallback (optional deps only)
    uv = shutil.which("uv")
    if uv and needs:
        prefix = [uv, "run", "--no-project"]
        for pkg in needs:
            pip = {"imagehash": "imagehash", "PIL": "pillow", "fal_client": "fal-client"}.get(pkg, pkg)
            prefix += ["--with", pip]
        prefix += ["python3"]
        return prefix, "uv:" + ",".join(needs)
    # last resort: current interpreter, let it fail loudly downstream
    return [sys.executable], sys.executable


def gen_one(idx, seed, args, gen_interp):
    """One cheap falgen candidate. Returns a result dict (never raises)."""
    out = f"{args.out_prefix}_c{idx}.png"
    mode = OP_TO_MODE[args.op]
    cmd = gen_interp + [
        str(SCRIPTS / "falgen.py"),
        "--mode", mode,
        "--image", args.image,
        "--out", out,
        "--maxside", str(args.maxside),
        "--seed", str(seed),
        "--feather", str(args.feather),
    ]
    if args.mask:
        cmd += ["--mask", args.mask]
    prompt = args.prompt or args.desc or ""
    cmd += ["--prompt", prompt]
    t0 = time.monotonic()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
    dt = time.monotonic() - t0
    ok = r.returncode == 0 and Path(_resolve(out)).exists()
    return {
        "idx": idx, "seed": seed, "out": out, "ok": ok, "seconds": round(dt, 1),
        "stdout": r.stdout.strip().splitlines()[-1:] if r.stdout.strip() else [],
        "stderr": r.stderr.strip().splitlines()[-2:] if (not ok and r.stderr.strip()) else [],
    }


def _resolve(p):
    pp = Path(p)
    return pp if pp.is_absolute() else (ROOT / pp)


def run_sweep(candidates, criterion):
    """Dedup + pairwise tournament. Returns (winner_path, raw_stdout, err)."""
    needs = []
    # sweep only needs imagehash for dedup (optional) + requests via judge.
    # Use an interpreter that has imagehash if possible, else degrade (no dedup).
    sweep_interp, _ = _interp_for(["imagehash"])
    cmd = sweep_interp + [str(SCRIPTS / "sweep.py"), "--criterion", criterion,
                          "--candidates"] + candidates
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    raw = r.stdout
    if r.returncode != 0:
        return None, raw, (r.stderr.strip()[-400:] or f"sweep exit {r.returncode}")
    m = list(WINNER_RE.finditer(raw))
    if not m:
        return None, raw, "could not parse WINNER from sweep output"
    return m[-1].group(1).strip(), raw, None


def main():
    ap = argparse.ArgumentParser(description="SCOUT-then-FINAL cheap-candidate picker.")
    ap.add_argument("--image", required=True, help="context crop fed to the model")
    ap.add_argument("--mask", help="white=repaint mask (for redraw/fill)")
    ap.add_argument("--op", default="redraw", choices=list(OP_TO_MODE))
    ap.add_argument("--prompt", help="redraw prompt")
    ap.add_argument("--desc", help="alias for --prompt")
    ap.add_argument("--n", type=int, default=3, help="number of cheap candidates")
    ap.add_argument("--maxside", type=int, default=768, help="SCOUT longer-side px (cheap)")
    ap.add_argument("--final-maxside", type=int, default=1400, help="FINAL longer-side px")
    ap.add_argument("--feather", type=int, default=24)
    ap.add_argument("--seed-base", type=int, default=1000, help="seeds = base, base+1, ...")
    ap.add_argument("--criterion", help="judge criterion (defaults from prompt)")
    ap.add_argument("--out-prefix", default="tasks/improve/_scout",
                    help="candidates -> <prefix>_cN.png ; final -> <prefix>_final.png")
    ap.add_argument("--concurrency", type=int, default=0,
                    help="parallel gens (0 = all N at once)")
    ap.add_argument("--timeout", type=float, default=300.0, help="per-gen timeout (s)")
    args = ap.parse_args()

    if not (args.prompt or args.desc):
        ap.error("need --prompt or --desc")
    if args.op == "redraw" and not args.mask:
        ap.error("redraw needs --mask")
    Path(_resolve(args.out_prefix)).parent.mkdir(parents=True, exist_ok=True)

    prompt = args.prompt or args.desc
    criterion = args.criterion or (
        f"cleanest, best-formed result for: {prompt}. "
        "Correct anatomy/shape, matches surrounding watercolor+ink style, no text, no defects."
    )
    gen_interp, gen_label = _interp_for(["requests", "PIL"])
    print(f"[scout] op={args.op} mode={OP_TO_MODE[args.op]} n={args.n} "
          f"scout-maxside={args.maxside} final-maxside={args.final_maxside}")
    print(f"[scout] gen interpreter: {gen_label}")

    seeds = [args.seed_base + i for i in range(args.n)]

    # ---- Step 1: SCOUT (cheap candidates in parallel) ----
    wall0 = time.monotonic()
    workers = args.concurrency if args.concurrency > 0 else args.n
    cand_results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(gen_one, i + 1, seeds[i], args, gen_interp): i for i in range(args.n)}
        for f in as_completed(futs):
            res = f.result()
            cand_results.append(res)
            tag = "OK" if res["ok"] else "FAIL"
            print(f"[scout]   cand c{res['idx']} seed={res['seed']} {tag} {res['seconds']}s")
            if not res["ok"] and res["stderr"]:
                print("           " + " | ".join(res["stderr"]), file=sys.stderr)
    cand_results.sort(key=lambda r: r["idx"])
    scout_wall = time.monotonic() - wall0

    good = [r for r in cand_results if r["ok"]]
    if not good:
        log = {"ok": False, "stage": "scout", "error": "all candidates failed",
               "candidates": cand_results}
        _write_log(args, log)
        print("[scout] FAIL: no candidate generated", file=sys.stderr)
        sys.exit(1)

    cand_paths = [r["out"] for r in good]

    # ---- Step 2: PICK (sweep = dedup + pairwise judge) ----
    print(f"[scout] sweep over {len(cand_paths)} candidate(s) ...")
    pick_t0 = time.monotonic()
    if len(cand_paths) == 1:
        winner_path, sweep_raw, sweep_err = cand_paths[0], "(single candidate, no tournament)", None
    else:
        winner_path, sweep_raw, sweep_err = run_sweep(cand_paths, criterion)
    pick_wall = time.monotonic() - pick_t0

    if sweep_err and winner_path is None:
        log = {"ok": False, "stage": "sweep", "error": sweep_err,
               "candidates": cand_results, "sweep_stdout": sweep_raw}
        _write_log(args, log)
        print(f"[scout] FAIL: sweep/judge error: {sweep_err}", file=sys.stderr)
        sys.exit(2)

    # map winner path back to its candidate (-> seed)
    win_name = Path(winner_path).name
    winner = next((r for r in good if Path(r["out"]).name == win_name), None)
    if winner is None:
        winner = good[0]
        print(f"[scout] warn: winner '{win_name}' not matched, defaulting to {Path(winner['out']).name}",
              file=sys.stderr)
    print(f"[scout] WINNER: c{winner['idx']} seed={winner['seed']} ({Path(winner['out']).name})")

    # ---- Step 3: FINAL (re-render winner at full res) ----
    final_out = f"{args.out_prefix}_final.png"
    final_cmd = gen_interp + [
        str(SCRIPTS / "falgen.py"),
        "--mode", OP_TO_MODE[args.op],
        "--image", args.image,
        "--out", final_out,
        "--maxside", str(args.final_maxside),
        "--seed", str(winner["seed"]),
        "--feather", str(args.feather),
        "--prompt", prompt,
    ]
    if args.mask:
        final_cmd += ["--mask", args.mask]
    print(f"[scout] FINAL render winner @ maxside={args.final_maxside} ...")
    final_t0 = time.monotonic()
    fr = subprocess.run(final_cmd, capture_output=True, text=True, timeout=args.timeout)
    final_wall = time.monotonic() - final_t0
    final_ok = fr.returncode == 0 and Path(_resolve(final_out)).exists()
    if not final_ok:
        log = {"ok": False, "stage": "final", "error": (fr.stderr.strip()[-400:] or "final render failed"),
               "candidates": cand_results, "winner_idx": winner["idx"], "sweep_stdout": sweep_raw}
        _write_log(args, log)
        print(f"[scout] FAIL: final render failed: {fr.stderr.strip()[-200:]}", file=sys.stderr)
        sys.exit(3)

    total_wall = time.monotonic() - wall0
    # cost model: scout did N cheap gens + 1 full; baseline = N full gens.
    log = {
        "ok": True,
        "op": args.op, "mode": OP_TO_MODE[args.op], "prompt": prompt,
        "n": args.n, "scout_maxside": args.maxside, "final_maxside": args.final_maxside,
        "candidates": cand_results,
        "winner": {"idx": winner["idx"], "seed": winner["seed"],
                   "scout_png": winner["out"], "final_png": final_out},
        "sweep_stdout": sweep_raw,
        "timing": {
            "scout_wall_s": round(scout_wall, 1),
            "pick_wall_s": round(pick_wall, 1),
            "final_wall_s": round(final_wall, 1),
            "total_wall_s": round(total_wall, 1),
            "slowest_scout_gen_s": round(max((r["seconds"] for r in good), default=0), 1),
            "final_gen_s": round(final_wall, 1),
        },
    }
    _write_log(args, log)
    print(f"[scout] DONE  final={final_out}")
    print(f"[scout] timing: scout={scout_wall:.1f}s  pick={pick_wall:.1f}s  "
          f"final={final_wall:.1f}s  total={total_wall:.1f}s")
    print(f"[scout] log -> {args.out_prefix}_log.json")


def _write_log(args, log):
    p = _resolve(f"{args.out_prefix}_log.json")
    p.write_text(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
