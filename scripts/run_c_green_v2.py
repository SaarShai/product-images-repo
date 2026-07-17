#!/usr/bin/env python3
"""run_c_green_v2.py — THE canonical one-command Route C-green v2 runner.

Route C-green v2 (`gpt-image-2`-forced chroma-key transparent-art pipeline,
user-validated 2026-07-13, "best yet — bank it"). See
`tasks/transparent-bg-endgame/PIPELINE.md` ("ROUTE C-green v2") and
`skills/transparent-product-image-gen/SKILL.md` (same section) for the full
recipe and rationale this runner encodes.

Usage:
    /usr/bin/python3 scripts/run_c_green_v2.py \\
      --subject "a single watercolor coral cluster ..." \\
      --out-root /path/to/out --eligibility-confirmed \\
      [--n 2] [--size 1024x1536] [--skip-gen raw.png] [--ppi 300]

Stages: preflight -> prompt assemble+lint -> generate (Responses API async
job, gpt-image-2, or --skip-gen to reuse a stored raw) -> chroma_key ->
decontam_binarize -> green_purge --no-green-art --erode 2 --band 6 ->
gate_battery --profile print [--ppi PPI] -> review_pack.

--n must be >= 1 (n=0 is a hard-fail config error, not zero-work success).
--skip-gen always reuses exactly one raw; a --n > 1 alongside it is clamped
to 1 with a loud stderr WARNING (not silently accepted).
--ppi passes panel pixels-per-inch through to gate_battery so D1/D2/D4 mm
thresholds are calibrated; without it, --profile print degrades to pixel
fallbacks and manifest.json records physical_units:false with a WARNING.

Exit codes preserve gate_battery's own tri-state contract verbatim, worst-of
across all candidates -- REVIEW is NEVER silently promoted to PASS:
  0 (PASS)   — every candidate's gate verdict is PASS.
  3 (REVIEW) — at least one candidate is REVIEW (advisory or not) and none is
               FAIL; manifest.json sets human_review_required:true. A human
               must approve before this counts as shipped.
  2 (FAIL)   — any hard failure: preflight, gen/poll error, a pipeline stage
               subprocess failing, a candidate gate verdict of FAIL, a
               gate_battery crash (any exit code other than 0/3/2), or zero
               candidates processed. manifest.json is still written (with the
               failure recorded) before returning, even on gen/poll failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
PY = "/usr/bin/python3"

sys.path.insert(0, str(SCRIPTS))
import prompt_blocks_c_green_v2 as blocks  # noqa: E402
import review_pack  # noqa: E402

ELIGIBILITY_CHECKLIST = """\
Route C-green v2 eligibility checklist (answer honestly before spending a
generation):
  [ ] Ink outlines acceptable? — the recipe MANDATES a visible dark ink
      contour around every shape (SIGNIFICANT_CONTOUR_BLOCK). If the product
      needs lineless/soft watercolor edges, this route is the wrong tool.
  [ ] No essential green content? — NO_GREEN_ART_BLOCK bans bright/pure green
      anywhere in the subject (green_purge --no-green-art then destroys ALL
      key-hue green unconditionally). If the subject NEEDS true green
      (e.g. a green product), this route will damage it.
  [ ] Filaments simplifiable? — NO_FILAMENT_BLOCK requires thin
      fronds/antennae/hairlines to merge into solid painted joints. If the
      subject's identity depends on isolated hair-thin strands, this route
      will alter that geometry.
Re-run with --eligibility-confirmed once you have verified all three for this
subject.
"""

GREEN_HEX = blocks.GREEN_HEX
RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
GEN_MODEL = "gpt-image-2"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True, check=True
        ).stdout.strip()
    except Exception:
        return "unknown"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fail(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 2


# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------


def preflight(need_gen: bool) -> list[str]:
    """Returns a list of problems; empty list = OK."""
    problems: list[str] = []
    try:
        import numpy, PIL, scipy  # noqa: F401
    except ImportError as exc:
        problems.append(f"missing python dependency: {exc}. Run with /usr/bin/python3, not bare python3.")

    for rel in (
        "scripts/chroma_key.py",
        "scripts/decontam_binarize.py",
        "scripts/green_purge.py",
        "scripts/gates/gate_battery.py",
        "scripts/prompt_blocks_c_green_v2.py",
        "scripts/review_pack.py",
        "scripts/_falcommon.py",
    ):
        if not (REPO / rel).exists():
            problems.append(f"missing required script: {rel}")

    if need_gen:
        try:
            sys.path.insert(0, str(SCRIPTS))
            from _falcommon import load_openai_key

            load_openai_key()
        except SystemExit as exc:
            problems.append(f"OPENAI_API_KEY not available: {exc}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"OPENAI_API_KEY check failed: {exc}")
    return problems


# ---------------------------------------------------------------------------
# Generation (Responses API async job; reused verbatim recipe from
# round4_key/gen_round4.py::submit/poll/extract_b64, cited by PIPELINE.md)
# ---------------------------------------------------------------------------


def submit_job(key: str, prompt: str, size: str, n: int) -> list[str]:
    import requests

    ids = []
    for _ in range(n):
        payload = {
            "model": "gpt-5",
            "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
            "tools": [
                {"type": "image_generation", "model": GEN_MODEL, "quality": "high", "size": size}
            ],
            "background": True,
        }
        resp = requests.post(
            RESPONSES_ENDPOINT,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"submit failed HTTP {resp.status_code}: {resp.text[:500]}")
        ids.append(resp.json()["id"])
    return ids


def poll_job(key: str, response_id: str, timeout_s: int = 900) -> dict:
    import requests

    t0 = time.time()
    while time.time() - t0 < timeout_s:
        resp = requests.get(
            f"{RESPONSES_ENDPOINT}/{response_id}",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(
                f"poll failed HTTP {resp.status_code} for job {response_id}: {resp.text[:500]}"
            )
        job = resp.json()
        if job.get("status") in ("completed", "failed", "cancelled", "incomplete"):
            return job
        time.sleep(5)
    raise TimeoutError(f"job {response_id} timed out after {timeout_s}s")


def extract_b64(job: dict) -> str | None:
    for item in job.get("output", []):
        if item.get("type") == "image_generation_call" and item.get("result"):
            return item["result"]
    return None


# ---------------------------------------------------------------------------
# Pipeline stages (subprocess calls to the existing CLI tools)
# ---------------------------------------------------------------------------


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    print("+ " + " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, capture_output=True, text=True)


GATE_RC_TO_VERDICT = {0: "PASS", 3: "REVIEW", 2: "FAIL"}


def run_one_candidate(
    cand_dir: Path,
    raw_path: Path,
    manifest_entry: dict,
    ppi: float | None = None,
) -> dict:
    """Run chroma_key -> decontam_binarize -> green_purge -> gate_battery ->
    review_pack on one raw. Returns {"stage_results":..., "verdict":..., "ok":bool}.

    verdict is one of PASS/REVIEW/FAIL, taken from gate_battery's own exit
    code (0/3/2) faithfully -- REVIEW is never silently promoted to "ok"."""
    cand_dir.mkdir(parents=True, exist_ok=True)
    keyed = cand_dir / "keyed.png"
    key_json = cand_dir / "keyed.json"
    decontam = cand_dir / "decontam.png"
    purged = cand_dir / "purged.png"
    purge_json = cand_dir / "purged.json"
    gates_dir = cand_dir / "gates"
    pack_dir = cand_dir / "review_pack"

    stages = []

    r = run_cmd([PY, str(SCRIPTS / "chroma_key.py"), "key", str(raw_path), str(keyed), "--json", str(key_json)])
    stages.append({"stage": "chroma_key", "returncode": r.returncode, "stderr": r.stderr[-2000:]})
    if r.returncode != 0:
        return {"stage_results": stages, "verdict": "FAIL", "ok": False}

    r = run_cmd(
        [
            PY, str(SCRIPTS / "decontam_binarize.py"),
            "--rgba", str(keyed), "--out", str(decontam), "--bg-color", GREEN_HEX,
        ]
    )
    stages.append({"stage": "decontam_binarize", "returncode": r.returncode, "stderr": r.stderr[-2000:]})
    if r.returncode != 0:
        return {"stage_results": stages, "verdict": "FAIL", "ok": False}

    r = run_cmd(
        [
            PY, str(SCRIPTS / "green_purge.py"), str(decontam), str(purged),
            "--no-green-art", "--erode", "2", "--band", "6", "--json", str(purge_json),
        ]
    )
    stages.append({"stage": "green_purge", "returncode": r.returncode, "stderr": r.stderr[-2000:]})
    if r.returncode != 0:
        return {"stage_results": stages, "verdict": "FAIL", "ok": False}

    gate_cmd = [
        PY, str(SCRIPTS / "gates" / "gate_battery.py"),
        "--rgba", str(purged), "--source", str(raw_path), "--bg-color", GREEN_HEX,
        "--profile", "print", "--out-dir", str(gates_dir),
    ]
    if ppi is not None:
        gate_cmd += ["--ppi", str(ppi)]
    r = run_cmd(gate_cmd)
    gate_rc = r.returncode
    stages.append({"stage": "gate_battery", "returncode": gate_rc, "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]})

    battery_path = gates_dir / "battery.json"
    battery = json.loads(battery_path.read_text()) if battery_path.exists() else None

    # gate_battery's own exit code (0/3/2 = PASS/REVIEW/FAIL) is the gate
    # contract; map it through faithfully. Any other code is a crash and
    # must be a hard fail, never silently treated as PASS/REVIEW.
    if gate_rc in GATE_RC_TO_VERDICT:
        verdict = GATE_RC_TO_VERDICT[gate_rc]
        if battery is not None and battery.get("verdict") != verdict:
            stages[-1]["verdict_mismatch"] = {
                "from_exit_code": verdict, "from_battery_json": battery.get("verdict"),
            }
    else:
        verdict = "FAIL"
        stages[-1]["crash"] = True
        stages[-1]["note"] = f"gate_battery exited with unexpected code {gate_rc}; treated as hard FAIL"

    advisory_only = False
    if battery and verdict == "REVIEW":
        non_pass = [g for g in battery["gates"].values() if g["verdict"] != "PASS"]
        advisory_only = all(g.get("advisory") for g in non_pass)

    manifest_entry["final_sha256"] = sha256_file(purged) if purged.exists() else None
    # record the battery's own verdict verbatim (never an invented approval)
    manifest_entry["gate_verdict"] = battery["verdict"] if battery else verdict
    manifest_entry["gate_advisory_only"] = advisory_only

    # review pack — build regardless of verdict so REVIEW candidates get eyes
    pack_manifest = review_pack.build_review_pack(
        final_path=purged, raw_path=raw_path, out_dir=pack_dir, gate_dir=gates_dir,
    )
    stages.append({"stage": "review_pack", "n_files": len(pack_manifest["files"])})

    # ok means TRUE PASS only. REVIEW is never auto-promoted to success --
    # it always requires a human, recorded via manifest["human_review_required"].
    ok = verdict == "PASS"
    return {"stage_results": stages, "verdict": verdict, "advisory_only": advisory_only, "ok": ok}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


VERDICT_RANK = {"PASS": 0, "REVIEW": 1, "FAIL": 2}
VERDICT_TO_EXIT = {"PASS": 0, "REVIEW": 3, "FAIL": 2}


def _fail_run(manifest: dict, run_dir: Path, error: str) -> int:
    """Write manifest.json with the failure recorded (forensic record) and
    return the hard-fail exit code. Every gen/poll failure MUST go through
    this so a failed run still leaves a manifest on disk."""
    manifest["finished_at"] = now_iso()
    manifest["error"] = error
    manifest["overall_verdict"] = "FAIL"
    manifest["overall_ok"] = False
    manifest["human_review_required"] = False
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"FAIL: {error}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--out-root", required=True, type=Path)
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--size", default="1024x1536")
    ap.add_argument("--skip-gen", type=Path, default=None, help="reuse an existing raw instead of generating")
    ap.add_argument("--eligibility-confirmed", action="store_true")
    ap.add_argument(
        "--ppi", type=float, default=None,
        help="panel pixels-per-inch for physical-unit gate thresholds (D1/D2/D4); "
        "passed through to gate_battery.py --ppi. Without it, --profile print "
        "gates degrade to pixel fallbacks (physical_units:false in manifest.json).",
    )
    args = ap.parse_args(argv)

    if args.n < 1:
        print(f"FAIL: --n must be >= 1 (got {args.n})", file=sys.stderr)
        return 2

    if args.skip_gen is not None and args.n != 1:
        # --skip-gen always reuses exactly one raw; clamp with a loud warning
        # rather than silently yielding 1 candidate while --n claims more.
        print(
            f"WARNING: --skip-gen reuses exactly one raw; --n {args.n} is ignored "
            "and clamped to 1 candidate.",
            file=sys.stderr,
        )

    if not args.eligibility_confirmed:
        print(ELIGIBILITY_CHECKLIST)
        return 2

    need_gen = args.skip_gen is None
    problems = preflight(need_gen)
    if problems:
        for p in problems:
            print(f"PREFLIGHT FAIL: {p}", file=sys.stderr)
        return 2

    prompt, prompt_sha = blocks.assemble_prompt(args.subject)
    print(f"prompt assembled, sha256={prompt_sha}, {len(prompt)} chars")

    import uuid

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    run_dir = args.out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(prompt)

    physical_units = args.ppi is not None
    if not physical_units:
        print(
            "WARNING: no --ppi given; this runner always gates at --profile print, "
            "so D1/D2/D4 mm thresholds are UNAVAILABLE and fall back to pixel "
            "heuristics (degraded, not calibrated). Pass --ppi <panel ppi> for a "
            "trustworthy print-profile run.",
            file=sys.stderr,
        )

    manifest: dict = {
        "run_id": run_id,
        "started_at": now_iso(),
        "args": {
            "subject": args.subject,
            "out_root": str(args.out_root),
            "n": args.n,
            "size": args.size,
            "skip_gen": str(args.skip_gen) if args.skip_gen else None,
            "ppi": args.ppi,
        },
        "prompt_sha256": prompt_sha,
        "model": GEN_MODEL,
        "script_git_commit": git_commit(),
        "physical_units": physical_units,
        "candidates": [],
    }

    raws: list[tuple[Path, dict]] = []

    if args.skip_gen is not None:
        if not args.skip_gen.exists():
            return _fail_run(manifest, run_dir, f"--skip-gen path does not exist: {args.skip_gen}")
        raw_sha = sha256_file(args.skip_gen)
        entry = {
            "id": "skip-gen-1",
            "source": "skip-gen",
            "raw_path": str(args.skip_gen),
            "raw_sha256": raw_sha,
            "prompt_sha256_at_gen": None,
            "note": "reused an existing raw; stored prompt-hash not verified because none was recorded for this file",
        }
        raws.append((args.skip_gen, entry))
    else:
        sys.path.insert(0, str(SCRIPTS))
        from _falcommon import load_openai_key

        key = load_openai_key()
        try:
            response_ids = submit_job(key, prompt, args.size, args.n)
        except Exception as exc:  # noqa: BLE001
            return _fail_run(manifest, run_dir, f"generation submit failed: {exc}")
        for i, rid in enumerate(response_ids, start=1):
            try:
                job = poll_job(key, rid)
                b64 = extract_b64(job)
                if not b64:
                    raise RuntimeError(f"no image result: {job.get('error') or job.get('status')}")
            except Exception as exc:  # noqa: BLE001
                return _fail_run(manifest, run_dir, f"generation {i} failed: {exc}")
            import base64

            raw_path = run_dir / f"raw_{i}.png"
            raw_path.write_bytes(base64.b64decode(b64))
            entry = {
                "id": f"gen-{i}",
                "source": "generated",
                "response_id": rid,
                "raw_path": str(raw_path),
                "raw_sha256": sha256_file(raw_path),
                "prompt_sha256_at_gen": prompt_sha,
            }
            raws.append((raw_path, entry))

    if not raws:
        return _fail_run(manifest, run_dir, "zero candidates were processed (no raws to run the pipeline on)")

    for i, (raw_path, entry) in enumerate(raws, start=1):
        cand_dir = run_dir / f"candidate_{i}"
        result = run_one_candidate(cand_dir, raw_path, entry, ppi=args.ppi)
        entry["cand_dir"] = str(cand_dir)
        entry["pipeline"] = result
        manifest["candidates"].append(entry)

    # tri-state overall verdict, worst-of across candidates. REVIEW is never
    # silently promoted to success -- it always exits 3 and requires a human.
    overall_verdict = "PASS"
    for entry in manifest["candidates"]:
        v = entry["pipeline"]["verdict"]
        if VERDICT_RANK.get(v, 2) > VERDICT_RANK.get(overall_verdict, 0):
            overall_verdict = v

    manifest["finished_at"] = now_iso()
    manifest["overall_verdict"] = overall_verdict
    manifest["overall_ok"] = overall_verdict == "PASS"
    manifest["human_review_required"] = any(
        entry["pipeline"]["verdict"] == "REVIEW" for entry in manifest["candidates"]
    )
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(json.dumps({
        "run_dir": str(run_dir),
        "overall_verdict": overall_verdict,
        "overall_ok": manifest["overall_ok"],
        "human_review_required": manifest["human_review_required"],
    }, indent=2))
    return VERDICT_TO_EXIT[overall_verdict]


if __name__ == "__main__":
    raise SystemExit(main())
