from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load_module("bg_benchmark_verifier", HERE / "verify_bg_solution.py")
fixture_builder = load_module("bg_benchmark_fixture_builder", HERE / "build_negative_fixtures.py")


@pytest.fixture(scope="module")
def fixture_manifest(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return fixture_builder.build_fixture_set(tmp_path_factory.mktemp("bg-negative-fixtures"))


def run_fixture_case(manifest_path: Path, case_id: str):
    return verifier.verify_manifest(manifest_path, {}, selected_cases=[case_id])


def failure_codes(report):
    return {item["code"] for item in report["reports"][0]["failures"]}


def test_good_fixture_passes_all_machine_checks(fixture_manifest: Path):
    report = run_fixture_case(fixture_manifest, "good")

    assert report["machine_pass"] is True
    assert report["reports"][0]["final_verdict"] == "PASS"
    assert report["reports"][0]["failures"] == []
    assert set(report["reports"][0]["composites"]) == {"white", "gray", "black", "magenta"}


@pytest.mark.parametrize(
    "case_id,expected_code",
    [
        ("negative-white-fringe", "white_edge_contamination"),
        ("negative-deleted-foreground", "deleted_foreground"),
        ("negative-retained-enclosed-bg", "enclosed_background_retained"),
        ("negative-bad-dimensions", "candidate_dimension_mismatch"),
        ("negative-missing-alpha", "alpha_channel_missing"),
        ("negative-wrong-format", "candidate_format_invalid"),
        ("negative-degenerate-alpha", "alpha_background_missing"),
        ("negative-premultiplied-rgb", "rgb_reconstruction"),
    ],
)
def test_each_negative_fixture_trips_intended_gate(
    fixture_manifest: Path, case_id: str, expected_code: str
):
    report = run_fixture_case(fixture_manifest, case_id)

    assert report["machine_pass"] is False
    assert expected_code in failure_codes(report)


def test_fixture_manifest_expected_matrix_matches_observed(fixture_manifest: Path):
    manifest = json.loads(fixture_manifest.read_text(encoding="utf-8"))

    for case in manifest["cases"]:
        report = run_fixture_case(fixture_manifest, case["id"])
        observed = failure_codes(report)
        for expected_code in case["expected_failure_codes"]:
            assert expected_code in observed, (case["id"], expected_code, observed)


def test_source_hash_and_dimensions_are_real_gates(tmp_path: Path):
    manifest_path = fixture_builder.build_fixture_set(tmp_path / "identity-gates")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    good = next(case for case in manifest["cases"] if case["id"] == "good")
    good["original"]["sha256"] = "0" * 64
    good["original"]["width"] = 65
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    report = run_fixture_case(manifest_path, "good")

    assert {"source_identity_mismatch", "source_dimension_mismatch"} <= failure_codes(report)


def test_human_review_is_pending_instead_of_auto_graded(tmp_path: Path):
    manifest_path = fixture_builder.build_fixture_set(tmp_path / "human-review")
    annotations_path = manifest_path.parent / "annotations.json"
    annotations = json.loads(annotations_path.read_text(encoding="utf-8"))
    annotations["human_review"] = [
        {
            "id": "ambiguous-watercolor-edge",
            "kind": "bbox",
            "bbox": [8, 12, 60, 52],
            "backgrounds": ["white", "gray", "black", "magenta"],
            "required": True,
        }
    ]
    annotations_path.write_text(json.dumps(annotations, indent=2) + "\n", encoding="utf-8")

    report = run_fixture_case(manifest_path, "good")

    assert report["machine_pass"] is True
    assert report["reports"][0]["final_verdict"] == "PENDING_HUMAN_REVIEW"


def test_real_manifest_freezes_all_three_ready_cases():
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    cases = {case["id"]: case for case in manifest["cases"]}
    expected = {
        "image14": {
            "original": "925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d",
            "x4": "7da93dcdd94c7d0c00dd28f71d8d59e1216c4bb63ee3b63351a0e3c4ba59970a",
            "size": (941, 1672),
            "x4_size": (3764, 6688),
        },
        "image15": {
            "original": "bf6f2deb7bce6e2b76a644d0caa7e3ae6519837c4d0842d47c548bc4fb650e72",
            "x4": "e97f55266e626af1030c53365b19dac0ffdc3eb2b15047c109be259f8a9f6477",
            "size": (1536, 1024),
            "x4_size": (6144, 4096),
        },
        "sample08": {
            "original": "8b0111dab8fb19887a83b8aaf8c6140e89d1b3e93b8b61265ab94e6ac3416af2",
            "x4": "afa9dcf1b9df607cb9587900af9a36b0fa719d50d41f71d9e3605934c34ccbdb",
            "size": (1634, 962),
            "x4_size": (6536, 3848),
        },
    }

    assert set(cases) == set(expected)
    assert not manifest.get("scaffolds")
    for case_id, frozen in expected.items():
        case = cases[case_id]
        references = {reference["scale"]: reference for reference in case["references"]}
        assert case["status"] == "ready"
        assert case["original"]["sha256"] == frozen["original"]
        assert (case["original"]["width"], case["original"]["height"]) == frozen["size"]
        assert references[1]["sha256"] == frozen["original"]
        assert references[4]["sha256"] == frozen["x4"]
        assert (references[4]["width"], references[4]["height"]) == frozen["x4_size"]
    assert cases["image15"]["paper_rgb"] == [250, 246, 241]
    assert "paper_rgb" not in cases["image14"]
    assert "paper_rgb" not in cases["sample08"]


@pytest.mark.parametrize("case_id", ["image14", "image15", "sample08"])
def test_ready_annotations_are_candidate_independent_and_cover_required_guards(case_id: str):
    manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
    case = next(row for row in manifest["cases"] if row["id"] == case_id)
    annotations = json.loads((HERE / case["annotations"]["path"]).read_text(encoding="utf-8"))
    width = case["original"]["width"]
    height = case["original"]["height"]

    assert annotations["case_id"] == case_id
    assert annotations["provenance"]["candidate_independent"] is True
    assert annotations["coordinate_space"]["width"] == width
    assert annotations["coordinate_space"]["height"] == height
    assert len(annotations["sure_foreground"]) >= 10
    assert len(annotations["sure_background_exterior"]) >= 6
    assert len(annotations["sure_background_enclosed"]) >= 4
    assert len(annotations["edge_probes"]) >= 3
    assert annotations["human_review"]
    assert all(row["required"] for row in annotations["human_review"])
    assert sum(row["alpha_min"] <= 64 for row in annotations["sure_foreground"]) >= 3
    assert all(row.get("why") for row in annotations["sure_foreground"])
    assert all(row.get("why") for row in annotations["sure_background_enclosed"])
    assert all(row.get("why") for row in annotations["edge_probes"])
    assert all(row.get("why") for row in annotations["human_review"])
    if case_id in {"image15", "sample08"}:
        audit = annotations["provenance"]["annotation_quality_audit"]
        assert audit["method"] == "source_only_semantic_boundary_review"
        assert "75 percent" in audit["rule"]
        assert all("PASS" in row["source_semantic_audit"] for row in annotations["edge_probes"])
    if case_id == "image15":
        assert annotations["paper_rgb"] == [250, 246, 241]
        paper_audit = annotations["provenance"]["paper_contract_audit"]
        assert paper_audit["representative_rgb"] == annotations["paper_rgb"]
        assert paper_audit["sample_count"] == 486

    all_ids = []
    for group in (
        "sure_foreground",
        "sure_background_exterior",
        "sure_background_enclosed",
    ):
        for guard in annotations[group]:
            x, y = guard["center"]
            radius = guard["radius"]
            assert radius <= x < width - radius
            assert radius <= y < height - radius
            all_ids.append(guard["id"])
    for probe in annotations["edge_probes"]:
        x0, y0, x1, y1 = probe["bbox"]
        assert 0 <= x0 < x1 <= width
        assert 0 <= y0 < y1 <= height
        all_ids.append(probe["id"])
    all_ids.extend(row["id"] for row in annotations["human_review"])
    assert len(all_ids) == len(set(all_ids))


def test_image15_freezes_the_authored_wash_decision_without_machine_labelling_terminal_fade():
    annotations = json.loads((HERE / "annotations/image15.json").read_text(encoding="utf-8"))
    contract = annotations["provenance"]["decision_contract"]
    review_ids = {row["id"] for row in annotations["human_review"]}
    foreground_ids = {row["id"] for row in annotations["sure_foreground"]}

    assert "foreground" in contract["authored_base_wash"]
    assert "background" in contract["uniform_paper"]
    assert "human review" in contract["terminal_fade"]
    assert {
        "fg-left-base-watercolor",
        "fg-center-sand-watercolor",
        "fg-right-sand-watercolor",
    } <= foreground_ids
    assert "review-terminal-base-fade" in review_ids


def test_negative_fixture_matrix_is_complete_and_each_negative_has_a_named_gate(
    fixture_manifest: Path,
):
    manifest = json.loads(fixture_manifest.read_text(encoding="utf-8"))
    expected = {
        "good": [],
        "negative-white-fringe": ["white_edge_contamination"],
        "negative-deleted-foreground": ["deleted_foreground"],
        "negative-retained-enclosed-bg": ["enclosed_background_retained"],
        "negative-bad-dimensions": ["candidate_dimension_mismatch"],
        "negative-missing-alpha": ["alpha_channel_missing"],
        "negative-wrong-format": ["candidate_format_invalid"],
        "negative-degenerate-alpha": ["alpha_background_missing"],
        "negative-premultiplied-rgb": ["rgb_reconstruction"],
    }

    observed = {case["id"]: case["expected_failure_codes"] for case in manifest["cases"]}
    assert observed == expected
    assert all(len(codes) == 1 for case_id, codes in observed.items() if case_id != "good")


def test_paper_rgb_resolution_prefers_case_then_annotation_then_global_contract():
    contract = {"paper_rgb": [255, 255, 255]}

    assert verifier.resolve_paper_rgb(
        {"paper_rgb": [250, 246, 241]}, {"paper_rgb": [250, 246, 241]}, contract
    ) == ([250, 246, 241], "case")
    assert verifier.resolve_paper_rgb({}, {"paper_rgb": [252, 250, 248]}, contract) == (
        [252, 250, 248],
        "annotation",
    )
    assert verifier.resolve_paper_rgb({}, {}, contract) == ([255, 255, 255], "contract")
    with pytest.raises(ValueError, match="disagree"):
        verifier.resolve_paper_rgb(
            {"paper_rgb": [250, 246, 241]}, {"paper_rgb": [255, 255, 255]}, contract
        )


def test_case_level_paper_rgb_drives_reconstruction_in_full_verifier(tmp_path: Path):
    manifest_path = fixture_builder.build_fixture_set(tmp_path / "case-paper-rgb")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    good = next(case for case in manifest["cases"] if case["id"] == "good")
    good["paper_rgb"] = [250, 246, 241]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    annotations_path = manifest_path.parent / "annotations.json"
    annotations = json.loads(annotations_path.read_text(encoding="utf-8"))
    annotations["paper_rgb"] = [250, 246, 241]
    annotations_path.write_text(json.dumps(annotations, indent=2) + "\n", encoding="utf-8")

    report = run_fixture_case(manifest_path, "good")
    case_report = report["reports"][0]

    assert case_report["paper_rgb"] == [250, 246, 241]
    assert case_report["paper_rgb_source"] == "case"
    assert "rgb_reconstruction" in failure_codes(report)
