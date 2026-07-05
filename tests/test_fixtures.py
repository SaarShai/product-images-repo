import json
import re
from pathlib import Path

import pytest

from studio.fixtures import iter_fixtures, load_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = load_manifest()
FIXTURES = MANIFEST["fixtures"]
FIXTURE_PATHS = [
    (fixture["id"], Path(path))
    for fixture in FIXTURES
    for path in fixture["paths"]
]
METRIC_JSON_PATHS = [
    (fixture, Path(path))
    for fixture in FIXTURES
    for path in fixture["paths"]
    if Path(path).name in {"region_iou.json", "judge.json"}
]
OPEN_PROBLEM_FIXTURES = [
    fixture for fixture in FIXTURES if fixture["kind"] in {"hands", "near_miss"}
]


def test_manifest_loads():
    kinds = {fixture["kind"] for fixture in FIXTURES}

    assert len(FIXTURES) >= 15
    assert len(kinds) >= 6
    assert list(iter_fixtures("judge_inversion"))[0]["id"] == "fx-judge-inversion-01"


@pytest.mark.parametrize("fixture_id,path", FIXTURE_PATHS)
def test_all_fixture_paths_exist(fixture_id, path):
    assert path.exists(), f"{fixture_id} path does not exist: {path}"


@pytest.mark.parametrize("fixture,json_path", METRIC_JSON_PATHS)
def test_geom_fixture_metrics(fixture, json_path):
    data = json.loads(json_path.read_text(encoding="utf-8"))

    if json_path.name == "region_iou.json":
        metric = data["mean_region_iou"]
        metric_field = "mean_region_iou"
    else:
        metric = _first_number(data["region_iou_agreement"])
        metric_field = "region_iou_agreement"

    if fixture["kind"] == "geom_good":
        assert metric >= 0.88, (
            f"{fixture['id']} expected good geometry, but {metric_field}={metric}"
        )
    elif fixture["kind"] in {"geom_bad", "judge_inversion"}:
        assert metric < 0.85, (
            f"{fixture['id']} expected bad geometry, but {metric_field}={metric}"
        )
    else:
        pytest.skip(f"{fixture['kind']} has no metric direction contract")

    assert str(round(metric, 3)) in fixture["expected"]


@pytest.mark.xfail(reason="open problem until P3", strict=True)
@pytest.mark.parametrize("fixture", OPEN_PROBLEM_FIXTURES, ids=lambda item: item["id"])
def test_open_problems_are_xfail(fixture):
    assert fixture.get("repaired_output_passes_gate") is True


def _first_number(value):
    match = re.search(r"\d+(?:\.\d+)?", value)
    if not match:
        raise AssertionError(f"no numeric metric found in region_iou_agreement: {value}")
    return float(match.group(0))
