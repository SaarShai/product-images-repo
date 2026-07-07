import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

from scripts import ref_lint


REPO = Path(__file__).resolve().parents[1]
REF_LINT = REPO / "scripts" / "ref_lint.py"


def _make_image(path: Path, color=(120, 140, 200)) -> Path:
    Image.new("RGB", (40, 30), color).save(path)
    return path


# --- dry-run prompt content (no network) ---


def test_dry_run_prints_prompts_no_api_call(tmp_path):
    img = _make_image(tmp_path / "ref.png")
    result = subprocess.run(
        [sys.executable, str(REF_LINT), "--image", str(img), "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["text_check"]["dry_run"] is True
    assert "text" in out["text_check"]["prompt"].lower()
    assert out["door_check"]["dry_run"] is True
    assert "door" in out["door_check"]["prompt"].lower()


def test_dry_run_prompts_mention_yes_no_semantics():
    # Prompts must ask a literal yes/no-style question per the brief.
    assert "readable text" in ref_lint.TEXT_PROMPT.lower()
    assert "logo" in ref_lint.TEXT_PROMPT.lower() or "watermark" in ref_lint.TEXT_PROMPT.lower()
    assert "open" in ref_lint.DOOR_PROMPT.lower()
    assert "door" in ref_lint.DOOR_PROMPT.lower()


# --- hold-out path-pattern matrix (no network) ---


def test_hold_out_rejects_generated_output_for_target_panel():
    assert ref_lint.hold_out_violation("round3/door/raws/s2.png", "door") is True
    assert ref_lint.hold_out_violation("tasks/door/outputs/candidate.png", "door") is True
    assert ref_lint.hold_out_violation("RESULTS/door/finals/final.png", "door") is True


def test_hold_out_accepts_original_source_art():
    assert ref_lint.hold_out_violation(
        "tasks/marriott-hospital/style-read/crop-hospital-facade.png", "door"
    ) is False
    assert ref_lint.hold_out_violation("refs/ref_police_facade.png", "door") is False


def test_hold_out_accepts_generated_output_for_a_different_panel():
    # Current rule scope: a generated output only violates hold-out for ITS OWN target panel.
    assert ref_lint.hold_out_violation("round2/window/raws/s1.png", "door") is False
    assert ref_lint.hold_out_violation("candidates/skyline/s3.png", "door") is False


def test_hold_out_empty_inputs_pass():
    assert ref_lint.hold_out_violation("", "door") is False
    assert ref_lint.hold_out_violation("round1/door/raws/s1.png", "") is False


def test_cli_hold_out_check_exit_codes():
    violation = subprocess.run(
        [sys.executable, str(REF_LINT), "--provenance", "round1/door/raws/s1.png", "--target-panel", "door"],
        capture_output=True,
        text=True,
    )
    assert violation.returncode == 2

    clean = subprocess.run(
        [sys.executable, str(REF_LINT), "--provenance", "style-read/crop.png", "--target-panel", "door"],
        capture_output=True,
        text=True,
    )
    assert clean.returncode == 0
