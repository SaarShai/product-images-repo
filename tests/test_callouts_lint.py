"""tests/test_callouts_lint.py — scripts/callouts_lint.py deterministic checks.

Synthetic YAML + geometry spec fixtures (no network, no real repo YAML edits).
"""
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
LINT = REPO / "scripts" / "callouts_lint.py"

SPEC = {
    "panel": "door",
    "size_px": [1692, 2400],
    "forbidden_bands_frac": [[0.143, 0.1838], [0.8156, 0.857]],
    "door_anchor_frac": [0.2705, 0.4001, 0.7293, 0.9864],
}


def _make_geom(tmp_path):
    geom = tmp_path / "geom"
    geom.mkdir()
    (geom / "door-spec.json").write_text(json.dumps(SPEC))
    return geom


def _run(callouts_path, geom_dir):
    r = subprocess.run(
        [sys.executable, str(LINT), "--callouts", str(callouts_path), "--geom", str(geom_dir)],
        capture_output=True, text=True,
    )
    return r.returncode, json.loads(r.stdout)


def _write_yaml(tmp_path, features, name="callouts.yaml"):
    doc = {"panel": "door", "contract": "v3", "features": features}
    p = tmp_path / name
    p.write_text(yaml.safe_dump(doc))
    return p


def test_clean_yaml_passes(tmp_path):
    geom = _make_geom(tmp_path)
    features = [
        {
            "feature_id": "cross_beacon",
            "zone_bbox_frac": [0.40, 0.02, 0.60, 0.13],  # well clear of bands + above anchor
            "layer": "architecture",
        },
        {
            "feature_id": "pinwheel_window",
            "zone_bbox_frac": [0.44, 0.135, 0.56, 0.195],
            "layer": "architecture",
        },
    ]
    yml = _write_yaml(tmp_path, features)
    code, rep = _run(yml, geom)
    assert code == 0
    assert rep["verdict"] == "PASS"
    assert rep["violations"] == []


def test_planted_forbidden_band_overlap_is_caught(tmp_path):
    geom = _make_geom(tmp_path)
    features = [
        {
            # sits right on top of the left forbidden band [0.143, 0.1838]
            "feature_id": "bad_band_feature",
            "zone_bbox_frac": [0.15, 0.50, 0.20, 0.60],
            "layer": "prop",
        },
    ]
    yml = _write_yaml(tmp_path, features)
    code, rep = _run(yml, geom)
    assert code == 2
    assert rep["verdict"] == "FAIL"
    assert any("bad_band_feature" in v and "forbidden" in v for v in rep["violations"])


def test_non_architecture_overlap_with_anchor_fails(tmp_path):
    geom = _make_geom(tmp_path)
    features = [
        {
            # deep inside door_anchor_frac, a 'prop' layer -> not exempt
            "feature_id": "teddy_patient",
            "zone_bbox_frac": [0.30, 0.45, 0.40, 0.55],
            "layer": "prop",
        },
    ]
    yml = _write_yaml(tmp_path, features)
    code, rep = _run(yml, geom)
    assert code == 2
    assert rep["verdict"] == "FAIL"
    assert any("teddy_patient" in v and "door portal" in v for v in rep["violations"])


def test_architecture_feature_fully_above_anchor_is_exempt(tmp_path):
    geom = _make_geom(tmp_path)
    # zone y1 == anchor y0 exactly (touches but does not extend into the anchor)
    features = [
        {
            "feature_id": "cross_badge",
            "zone_bbox_frac": [0.43, 0.30, 0.57, SPEC["door_anchor_frac"][1]],
            "layer": "architecture",
        },
    ]
    yml = _write_yaml(tmp_path, features)
    code, rep = _run(yml, geom)
    assert code == 0
    assert rep["verdict"] == "PASS"


def test_zone_outside_panel_frame_is_caught(tmp_path):
    geom = _make_geom(tmp_path)
    features = [
        {
            "feature_id": "off_panel",
            "zone_bbox_frac": [0.5, 0.5, 1.2, 0.6],  # x1 > 1.0
            "layer": "detail",
        },
    ]
    yml = _write_yaml(tmp_path, features)
    code, rep = _run(yml, geom)
    assert code == 2
    assert rep["verdict"] == "FAIL"
    assert any("off_panel" in v and "outside panel frame" in v for v in rep["violations"])


def test_real_repo_yaml_runs_and_reports_honestly():
    """Do not assert PASS/FAIL — just that the tool runs cleanly against the
    real feature-callouts-v1.yaml and returns machine-parseable JSON."""
    real_yaml = REPO / "tasks" / "marriott-hospital" / "style-spec" / "feature-callouts-v1.yaml"
    real_geom = REPO / "tasks" / "marriott-hospital" / "geometry" / "v3"
    code, rep = _run(real_yaml, real_geom)
    assert code in (0, 2)
    assert rep["verdict"] in ("PASS", "FAIL")
    assert "violations" in rep
