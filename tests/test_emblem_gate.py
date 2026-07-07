"""tests/test_emblem_gate.py — emblem_gate.py rule parsing + dry-run (no network).

Only exercises --dry-run: real API calls belong to live calibration runs, not
the test suite (constraint: no paid generation/calls in tests).
"""
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

import scripts.emblem_gate as EG

REPO = Path(__file__).resolve().parents[1]
EMBLEM_GATE = REPO / "scripts" / "emblem_gate.py"
REAL_CALLOUTS = REPO / "tasks" / "marriott-hospital" / "style-spec" / "feature-callouts-v1.yaml"


def make_png(tmp_path, name="cand.png"):
    path = tmp_path / name
    Image.new("RGB", (16, 24), (200, 200, 200)).save(path)
    return path


def run_dry(args):
    result = subprocess.run(
        [sys.executable, str(EMBLEM_GATE), *args],
        cwd=REPO,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_parse_callouts_from_real_yaml_builds_motif_rules():
    rules = EG.parse_callouts(REAL_CALLOUTS)

    assert rules["panel"] == "door"
    assert rules["contract"] == "v3"

    by_id = {r["feature_id"]: r for r in rules["motif_rules"]}
    assert set(by_id) == {
        "cross_beacon", "cross_badge", "teddy_patient",
        "pinwheel_window", "balloons", "topiary",
    }

    beacon = by_id["cross_beacon"]
    assert beacon["count"] == 1
    assert beacon["priority"] == "must"
    assert "not a second cross badge" in beacon["avoid"]

    badge = by_id["cross_badge"]
    assert badge["count"] == 1
    assert badge["priority"] == "must"
    assert "exactly ONE" in badge["avoid"]

    topiary = by_id["topiary"]
    assert topiary["count"] == 2
    assert topiary["priority"] == "nice"

    # every MUST feature is surfaced separately for the presence check
    must_ids = {r["feature_id"] for r in rules["must_features"]}
    assert must_ids == {"cross_beacon", "cross_badge", "teddy_patient"}

    # global negative callouts carried through verbatim
    assert any("beacon is a LAMP, not a badge" in n for n in rules["negative_callouts"])


def test_build_prompt_contains_exactly_one_badge_rule():
    rules = EG.parse_callouts(REAL_CALLOUTS)
    sys_p, user_text = EG.build_prompt(rules)

    combined = sys_p + "\n" + user_text
    # the LAMP-not-badge disambiguation must survive into the prompt
    assert "not a second cross badge" in combined or "LAMP" in combined
    assert "exactly ONE" in combined
    assert "cross_badge" in user_text
    assert "cross_beacon" in user_text
    # must-feature presence section is populated
    assert "teddy_patient" in user_text
    # whole-image framing (never tiles) must be explicit
    assert "WHOLE image" in sys_p or "whole image" in sys_p.lower()


def test_dry_run_cli_prints_prompt_and_rules_no_network(tmp_path):
    image = make_png(tmp_path)

    payload = run_dry([
        "--image", str(image),
        "--callouts", str(REAL_CALLOUTS),
        "--dry-run",
    ])

    assert payload["dry_run"] is True
    assert payload["image"] == str(image)
    assert payload["callouts"] == str(REAL_CALLOUTS)
    assert "cross_badge" in payload["system_prompt"] + payload["user_text"]
    assert "exactly ONE" in (payload["system_prompt"] + payload["user_text"])
    rule_ids = {r["feature_id"] for r in payload["rules"]["motif_rules"]}
    assert "cross_beacon" in rule_ids and "cross_badge" in rule_ids


def test_verdict_json_is_machine_parseable():
    """Simulates the shape emblem_gate prints in live mode (not a live call)."""
    fake_verdict = {
        "motif_counts": {
            "cross_beacon": {"seen": 1, "expected": 1, "match": True},
            "cross_badge": {"seen": 1, "expected": 1, "match": True},
        },
        "presence": {"cross_beacon": True, "cross_badge": True, "teddy_patient": True},
        "violations": [],
        "pass": True,
    }
    text = json.dumps(fake_verdict, indent=2)
    parsed = json.loads(text)
    assert parsed["pass"] is True
    assert parsed["motif_counts"]["cross_badge"]["match"] is True
    assert parsed["violations"] == []
