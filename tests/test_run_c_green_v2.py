"""run_c_green_v2.py two-phase runner tests: pre-purge human stop, SHA-bound
approval, and exit-code propagation. All tests use `--skip-gen` on a
generated-in-code raw fixture, so no network/API key is required -- the
generation stage is never reached."""
from __future__ import annotations

import glob
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_c_green_v2.py"

VERDICT_TO_EXIT = {"PASS": 0, "REVIEW": 3, "FAIL": 2}


def make_raw_disc(path: Path, size: int = 240) -> None:
    """A single warm-coral disc with a dark ink outline on a flat #00FF00
    field -- runs cleanly through chroma_key -> decontam_binarize ->
    green_purge (validated directly in tests/test_d5_preservation.py)."""
    scale = 4
    big = Image.new("RGB", (size * scale, size * scale), (0, 255, 0))
    draw = ImageDraw.Draw(big)
    cx = cy = size * scale // 2
    r = int(size * scale * 0.29)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(225, 120, 80))
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(25, 20, 15), width=6 * scale)
    big.resize((size, size), Image.LANCZOS).save(path)


def run_cli(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO,
        capture_output=True,
        text=True,
    )


def find_manifest(out_root: Path) -> dict:
    paths = glob.glob(str(out_root / "*" / "manifest.json"))
    assert paths, f"no manifest.json under {out_root}"
    return json.loads(Path(paths[0]).read_text())


def find_run_dir(out_root: Path) -> Path:
    paths = glob.glob(str(out_root / "*" / "manifest.json"))
    return Path(paths[0]).parent


# ---------------------------------------------------------------------------
# Config errors (fast-fail, before preflight/generation)
# ---------------------------------------------------------------------------


def test_approve_without_skip_gen_is_a_config_error():
    r = run_cli(["--subject", "x", "--out-root", "/tmp/nonexistent-c-green-v2", "--eligibility-confirmed", "--approve-prepurge-sha256", "deadbeef"])
    assert r.returncode == 2
    assert "--approve-prepurge-sha256 requires --skip-gen" in r.stderr


def test_named_policy_requires_ppi():
    r = run_cli(["--subject", "x", "--out-root", "/tmp/nonexistent-c-green-v2", "--eligibility-confirmed", "--policy", "cgreen-v2-print-binary-v1"])
    assert r.returncode == 2
    assert "requires --ppi" in r.stderr


def test_eligibility_not_confirmed_still_gates_first():
    r = run_cli(["--subject", "x", "--out-root", "/tmp/nonexistent-c-green-v2"])
    assert r.returncode == 2
    assert "eligibility checklist" in r.stdout.lower()


# ---------------------------------------------------------------------------
# Phase 1: pre-purge stop
# ---------------------------------------------------------------------------


def test_prepurge_stop_never_invokes_green_purge_and_records_sha(tmp_path):
    raw = tmp_path / "raw.png"
    make_raw_disc(raw)
    out_root = tmp_path / "out"

    r = run_cli(
        ["--subject", "test coral", "--out-root", str(out_root), "--eligibility-confirmed", "--ppi", "300", "--skip-gen", str(raw)]
    )
    assert r.returncode == 3, r.stdout + r.stderr

    manifest = find_manifest(out_root)
    assert manifest["mode"] == "prepurge_stop"
    assert manifest["overall_verdict"] == "REVIEW"
    assert manifest["human_review_required"] is True

    cand = manifest["candidates"][0]
    pipeline = cand["pipeline"]
    assert pipeline["phase"] == "prepurge_stop"
    assert pipeline["verdict"] == "REVIEW"
    assert pipeline["prepurge_sha256"], "prepurge_sha256 must be recorded"

    cand_dir = Path(cand["cand_dir"])
    decontam = cand_dir / "decontam.png"
    assert decontam.exists()

    import hashlib

    assert pipeline["prepurge_sha256"] == hashlib.sha256(decontam.read_bytes()).hexdigest()

    # green_purge must NEVER have run in this phase.
    assert not (cand_dir / "purged.png").exists()
    stage_names = [s.get("stage") for s in pipeline["stage_results"]]
    assert "green_purge" not in stage_names
    assert "d5_no_green_art_palette_precheck" in stage_names
    assert "d5_source_baseline_preservation_precheck" in stage_names
    assert (cand_dir / "prepurge_review_pack" / "manifest.json").exists()


# ---------------------------------------------------------------------------
# Phase 2: SHA-bound approval
# ---------------------------------------------------------------------------


def test_approve_correct_sha_proceeds_to_finalize_and_d5_passes(tmp_path):
    raw = tmp_path / "raw.png"
    make_raw_disc(raw)
    out_root_1 = tmp_path / "out1"
    out_root_2 = tmp_path / "out2"

    r1 = run_cli(
        ["--subject", "test coral", "--out-root", str(out_root_1), "--eligibility-confirmed", "--ppi", "300", "--skip-gen", str(raw)]
    )
    assert r1.returncode == 3, r1.stdout + r1.stderr
    manifest1 = find_manifest(out_root_1)
    prepurge_sha = manifest1["candidates"][0]["pipeline"]["prepurge_sha256"]

    r2 = run_cli(
        [
            "--subject", "test coral", "--out-root", str(out_root_2), "--eligibility-confirmed", "--ppi", "300",
            "--skip-gen", str(raw), "--approve-prepurge-sha256", prepurge_sha,
        ]
    )
    assert r2.returncode in (0, 3), r2.stdout + r2.stderr  # PASS or REVIEW (never a hard FAIL on a clean fixture)

    manifest2 = find_manifest(out_root_2)
    assert manifest2["mode"] == "finalize"
    cand = manifest2["candidates"][0]
    pipeline = cand["pipeline"]
    assert pipeline["phase"] == "finalize"
    cand_dir = Path(cand["cand_dir"])
    assert (cand_dir / "purged.png").exists()

    battery = json.loads((cand_dir / "gates" / "battery.json").read_text())
    d5 = battery["gates"]["D5_hole_gate"]
    assert d5["verdict"] == "PASS", d5
    assert d5["advisory"] is False
    assert d5["metric_values"]["aggregate_core_recall"] == 1.0

    # exit-code contract: gate_battery's own PASS/REVIEW/FAIL propagates
    # through the runner's 0/3/2 mapping, unmodified.
    assert r2.returncode == VERDICT_TO_EXIT[manifest2["overall_verdict"]]


def test_approve_wrong_sha_refuses_and_never_purges(tmp_path):
    raw = tmp_path / "raw.png"
    make_raw_disc(raw)
    out_root = tmp_path / "out"

    r = run_cli(
        [
            "--subject", "test coral", "--out-root", str(out_root), "--eligibility-confirmed", "--ppi", "300",
            "--skip-gen", str(raw), "--approve-prepurge-sha256", "0" * 64,
        ]
    )
    assert r.returncode == 2, r.stdout + r.stderr

    manifest = find_manifest(out_root)
    assert manifest["overall_verdict"] == "FAIL"
    cand = manifest["candidates"][0]
    pipeline = cand["pipeline"]
    assert pipeline["verdict"] == "FAIL"
    assert "mismatch" in pipeline["note"].lower()

    cand_dir = Path(cand["cand_dir"])
    assert not (cand_dir / "purged.png").exists()
    stage_names = [s.get("stage") for s in pipeline["stage_results"]]
    assert "green_purge" not in stage_names
    assert "approval_sha_check" in stage_names


def test_manifest_written_even_on_hard_fail(tmp_path):
    """Forensic record: manifest.json must exist on disk for the mismatch
    case too, not just on success (mirrors _fail_run's contract for
    gen/poll failures)."""
    raw = tmp_path / "raw.png"
    make_raw_disc(raw)
    out_root = tmp_path / "out"

    run_cli(
        [
            "--subject", "test coral", "--out-root", str(out_root), "--eligibility-confirmed", "--ppi", "300",
            "--skip-gen", str(raw), "--approve-prepurge-sha256", "1" * 64,
        ]
    )
    run_dir = find_run_dir(out_root)
    assert (run_dir / "manifest.json").exists()
