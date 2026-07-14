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
      [--n 2] [--size 1024x1536] [--skip-gen raw.png]

Stages: preflight -> prompt assemble+lint -> generate (Responses API async
job, gpt-image-2, or --skip-gen to reuse a stored raw) -> chroma_key ->
decontam_binarize -> green_purge --no-green-art --erode 2 --band 6 ->
gate_battery --profile print -> review_pack.

Exit 0: all candidates PASS or REVIEW(advisory-only) and a review pack was
built for each. Exit 2: any hard failure (preflight, gen error, gate FAIL not
advisory-only, etc).
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
    if sys.executable not in (PY, "/usr/bin/python3") and Path(sys.executable).resolve() != Path(PY).resolve():
        # Not fatal by itself (deps checked below), but flag clearly.
        pass
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
        job = requests.get(
            f"{RESPONSES_ENDPOINT}/{response_id}",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        ).json()
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


def run_one_candidate(
    cand_dir: Path,
    raw_path: Path,
    manifest_entry: dict,
) -> dict:
    """Run chroma_key -> decontam_binarize -> green_purge -> gate_battery ->
    review_pack on one raw. Returns {"stage_results":..., "verdict":..., "ok":bool}."""
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

    r = run_cmd(
        [
            PY, str(SCRIPTS / "gates" / "gate_battery.py"),
            "--rgba", str(purged), "--source", str(raw_path), "--bg-color", GREEN_HEX,
            "--profile", "print", "--out-dir", str(gates_dir),
        ]
    )
    stages.append({"stage": "gate_battery", "returncode": r.returncode, "stdout": r.stdout[-2000:], "stderr": r.stderr[-2000:]})

    battery_path = gates_dir / "battery.json"
    battery = json.loads(battery_path.read_text()) if battery_path.exists() else None
    verdict = battery["verdict"] if battery else "FAIL"
    advisory_only = False
    if battery and verdict == "REVIEW":
        non_pass = [g for g in battery["gates"].values() if g["verdict"] != "PASS"]
        advisory_only = all(g.get("advisory") for g in non_pass)

    manifest_entry["final_sha256"] = sha256_file(purged) if purged.exists() else None
    manifest_entry["gate_verdict"] = verdict
    manifest_entry["gate_advisory_only"] = advisory_only

    # review pack — build regardless of verdict so REVIEW candidates get eyes
    pack_manifest = review_pack.build_review_pack(
        final_path=purged, raw_path=raw_path, out_dir=pack_dir, gate_dir=gates_dir,
    )
    stages.append({"stage": "review_pack", "n_files": len(pack_manifest["files"])})

    ok = verdict == "PASS" or (verdict == "REVIEW" and advisory_only)
    return {"stage_results": stages, "verdict": verdict, "advisory_only": advisory_only, "ok": ok}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--out-root", required=True, type=Path)
    ap.add_argument("--n", type=int, default=2)
    ap.add_argument("--size", default="1024x1536")
    ap.add_argument("--skip-gen", type=Path, default=None, help="reuse an existing raw instead of generating")
    ap.add_argument("--eligibility-confirmed", action="store_true")
    args = ap.parse_args(argv)

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

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = args.out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "prompt.txt").write_text(prompt)

    manifest: dict = {
        "run_id": run_id,
        "started_at": now_iso(),
        "args": {
            "subject": args.subject,
            "out_root": str(args.out_root),
            "n": args.n,
            "size": args.size,
            "skip_gen": str(args.skip_gen) if args.skip_gen else None,
        },
        "prompt_sha256": prompt_sha,
        "model": GEN_MODEL,
        "script_git_commit": git_commit(),
        "candidates": [],
    }

    raws: list[tuple[Path, dict]] = []

    if args.skip_gen is not None:
        if not args.skip_gen.exists():
            print(f"FAIL: --skip-gen path does not exist: {args.skip_gen}", file=sys.stderr)
            return 2
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
            print(f"FAIL: generation submit failed: {exc}", file=sys.stderr)
            return 2
        for i, rid in enumerate(response_ids, start=1):
            try:
                job = poll_job(key, rid)
                b64 = extract_b64(job)
                if not b64:
                    raise RuntimeError(f"no image result: {job.get('error') or job.get('status')}")
            except Exception as exc:  # noqa: BLE001
                print(f"FAIL: generation {i} failed: {exc}", file=sys.stderr)
                return 2
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

    overall_ok = True
    for i, (raw_path, entry) in enumerate(raws, start=1):
        cand_dir = run_dir / f"candidate_{i}"
        result = run_one_candidate(cand_dir, raw_path, entry)
        entry["cand_dir"] = str(cand_dir)
        entry["pipeline"] = result
        overall_ok = overall_ok and result["ok"]
        manifest["candidates"].append(entry)

    manifest["finished_at"] = now_iso()
    manifest["overall_ok"] = overall_ok
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(json.dumps({"run_dir": str(run_dir), "overall_ok": overall_ok}, indent=2))
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
