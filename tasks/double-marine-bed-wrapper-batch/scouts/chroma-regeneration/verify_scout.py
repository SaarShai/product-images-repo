#!/usr/bin/env python3
"""Structural verifier for the frozen chroma-regeneration fleet."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
EXPECTED_IDS = {"openai-a", "nano-a", "flux2-a", "kontext-b"}
EXPECTED_PROMPT_HASHES = {
    "A": "c87bcfa1cd6c85502ce5f7dd7e8aad63de6ca8e93a70bc54c7332a9486b88ca0",
    "B": "5983f9a87d4bc16a7e0d285ce47a2cb22f864cadf1922db47c999c9ffd303f97",
}
EXPECTED_SOURCE_HASH = "925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d"
FORBIDDEN = re.compile(r"(?i)(FAL_KEY|authorization[:=]|data:image/|https?://[^\s\"]*(?:fal\.media|fal\.run))")
ROIS = {"cutout_01", "cutout_02", "fringe_00", "outer_soft", "enclosed_pocket", "sand_base"}
BENCHMARK_ZONES = {
    "edge-fish-translucent-fin",
    "edge-known-fringe-pink",
    "edge-right-pale-seaweed",
    "review-pale-sand-boundary",
    "review-cut00-pale-branches",
    "review-enclosed-triangle",
}
EXPECTED_BENCHMARK_FAILURES = {
    "flux2-a-direct": ["rgb_reconstruction"],
    "flux2-a": ["rgb_reconstruction", "deleted_foreground", "enclosed_background_retained"],
    "nano-a-direct": ["rgb_reconstruction"],
    "nano-a": [
        "rgb_reconstruction",
        "enclosed_background_retained",
        "white_edge_contamination",
        "white_edge_contamination",
    ],
    "assisted-r110": ["white_edge_contamination", "white_edge_contamination"],
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(out: Path) -> list[str]:
    errors = []
    manifest_path = out / "manifest.json"
    if not manifest_path.is_file():
        return ["missing manifest.json"]
    manifest = json.loads(manifest_path.read_text())
    records = manifest.get("new_candidates", [])
    ids = {record.get("id") for record in records}
    if ids != EXPECTED_IDS or len(records) != 4:
        errors.append(f"new candidate IDs/count mismatch: {ids}")
    if manifest.get("terminal_new_candidate_count") != 4 or manifest.get("valid_new_candidate_count") != 4:
        errors.append("not exactly four terminal valid new candidates")
    if manifest.get("target_key_hex_new_candidates") != "#00FF00":
        errors.append("new candidates do not share #00FF00")
    if manifest.get("source", {}).get("sha256") != EXPECTED_SOURCE_HASH:
        errors.append("source hash mismatch")
    if set(manifest.get("processed_candidate_ids", [])) != EXPECTED_IDS | {"prior-magenta"}:
        errors.append("processed candidate set mismatch")

    for record in records:
        candidate_id = record.get("id")
        family = record.get("prompt_family")
        if record.get("status") != "valid_output":
            errors.append(f"{candidate_id} not valid_output")
        if family not in EXPECTED_PROMPT_HASHES or record.get("prompt_sha256") != EXPECTED_PROMPT_HASHES.get(family):
            errors.append(f"{candidate_id} prompt family/hash mismatch")
        prompt_path = Path(record.get("prompt_path", ""))
        if not prompt_path.is_file() or sha256(prompt_path) != record.get("prompt_sha256"):
            errors.append(f"{candidate_id} prompt file missing/hash mismatch")
        if record.get("reference_sha256") != EXPECTED_SOURCE_HASH:
            errors.append(f"{candidate_id} missing original reference hash")
        if record.get("target_key_hex") != "#00FF00":
            errors.append(f"{candidate_id} wrong key")
        output = record.get("output", {})
        raw = Path(output.get("path", ""))
        if not raw.is_file() or sha256(raw) != output.get("sha256"):
            errors.append(f"{candidate_id} raw output missing/hash mismatch")
        elif Image.open(raw).size != (output.get("width"), output.get("height")):
            errors.append(f"{candidate_id} native dimensions mismatch")

    baseline = manifest.get("baseline", {})
    if baseline.get("id") != "prior-magenta" or baseline.get("target_key_hex") != "#FF00FF":
        errors.append("prior magenta baseline missing or mislabeled")

    style_path = Path(manifest.get("style_contract_path", ""))
    if not style_path.is_file() or sha256(style_path) != manifest.get("style_contract_sha256"):
        errors.append("style contract file missing/hash mismatch")

    for candidate_id in EXPECTED_IDS | {"prior-magenta"}:
        directory = out / candidate_id
        metrics_path = directory / "metrics.json"
        if not metrics_path.is_file():
            errors.append(f"{candidate_id} missing metrics")
            continue
        metrics = json.loads(metrics_path.read_text())
        if metrics.get("key_method") != "rgb_euclidean_to_target_only" or metrics.get("luma_used_for_keying") is not False:
            errors.append(f"{candidate_id} invalid key method")
        if metrics.get("transparent_radius_rgb") != 30.0 or metrics.get("opaque_radius_rgb") != 115.0:
            errors.append(f"{candidate_id} key thresholds drifted")
        required = [
            "raw.png", "keyed-no-despill.png", "keyed-rgba.png", "registered-analysis.png",
            "on-gray.png", "on-black.png", "on-magenta.png", "on-white.png", "full-board.jpg",
        ] + [f"crop-{name}.png" for name in ROIS]
        for name in required:
            if not (directory / name).is_file():
                errors.append(f"{candidate_id} missing {name}")
        keyed = directory / "keyed-rgba.png"
        no_despill = directory / "keyed-no-despill.png"
        if keyed.is_file() and no_despill.is_file():
            with Image.open(keyed) as keyed_image, Image.open(no_despill) as raw_keyed:
                if keyed_image.mode != "RGBA" or raw_keyed.mode != "RGBA":
                    errors.append(f"{candidate_id} keyed files not RGBA")
                elif not np.array_equal(np.asarray(keyed_image.getchannel("A")), np.asarray(raw_keyed.getchannel("A"))):
                    errors.append(f"{candidate_id} despill changed alpha")

    for path in out.rglob("*.json"):
        if FORBIDDEN.search(path.read_text(errors="replace")):
            errors.append(f"unredacted secret/data URI/provider URL in {path.relative_to(out)}")
    if not (out / "comparison-board.png").is_file():
        errors.append("missing comparison-board.png")
    hybrid = manifest.get("source_payload_hybrid", {})
    if set(hybrid.get("eligible_ids", [])) != {"flux2-a", "nano-a"}:
        errors.append("source-payload hybrid eligible IDs mismatch")
    if hybrid.get("status") != "frozen_benchmark_rejected_not_promotable":
        errors.append("source-payload hybrid final status mismatch")
    if not (out / "source-payload-hybrid-comparison.png").is_file():
        errors.append("missing source-payload-hybrid-comparison.png")
    for candidate_id in ("flux2-a", "nano-a"):
        direct_directory = out / candidate_id / "source-aligned-direct-key"
        for name in (
            "metrics.json",
            "registered-keyed-rgba.png",
            "on-white.png",
            "on-gray.png",
            "on-black.png",
            "on-magenta.png",
            "frozen-benchmark-report.json",
        ):
            if not (direct_directory / name).is_file():
                errors.append(f"{candidate_id} source-aligned direct analysis missing {name}")
        direct_rgba = direct_directory / "registered-keyed-rgba.png"
        if direct_rgba.is_file():
            with Image.open(direct_rgba) as image:
                if image.mode != "RGBA" or image.size != (941, 1672):
                    errors.append(f"{candidate_id} source-aligned direct RGBA shape/mode wrong")

        directory = out / candidate_id / "source-payload-hybrid"
        required_hybrid = [
            "metrics.json", "alpha-16bit.png", "source-payload-rgba.png", "full-board.jpg",
            "on-gray.png", "on-black.png", "on-magenta.png", "on-white.png",
        ] + [f"crop-{name}.png" for name in ROIS]
        for name in required_hybrid:
            if not (directory / name).is_file():
                errors.append(f"{candidate_id} hybrid missing {name}")
        metrics_path = directory / "metrics.json"
        if metrics_path.is_file():
            hybrid_metrics = json.loads(metrics_path.read_text())
            payload = hybrid_metrics.get("payload", {})
            if not hybrid_metrics.get("original_source_rgb_is_payload") or hybrid_metrics.get("candidate_rgb_used_in_final_payload") is not False:
                errors.append(f"{candidate_id} hybrid payload lineage wrong")
            if payload.get("maximum_rgb_delta_on_exact_interior") != 0:
                errors.append(f"{candidate_id} hybrid altered fully opaque source RGB")
        rgba_path = directory / "source-payload-rgba.png"
        if rgba_path.is_file():
            with Image.open(rgba_path) as image:
                if image.mode != "RGBA" or image.size != (941, 1672):
                    errors.append(f"{candidate_id} hybrid RGBA shape/mode wrong")

    final = manifest.get("final_evaluation", {})
    if final.get("status") != "complete_all_candidates_rejected":
        errors.append("final evaluation status missing or incorrect")
    summary_path = Path(final.get("comparison_summary", ""))
    if not summary_path.is_file() or sha256(summary_path) != final.get("comparison_summary_sha256"):
        errors.append("final comparison summary missing/hash mismatch")
    else:
        summary = json.loads(summary_path.read_text())
        if summary.get("schema") != "chroma-regeneration-final-comparison/v1":
            errors.append("final comparison summary schema mismatch")
        if summary.get("interpretation") != "All five frozen benchmark variants failed; boards are evidence, not approval.":
            errors.append("final comparison interpretation drifted")

    artifacts = final.get("artifacts", {})
    expected_artifacts = (
        {"full"}
        | {f"crop_{name}" for name in ROIS}
        | {f"benchmark_zone_{name}" for name in BENCHMARK_ZONES}
    )
    if set(artifacts) != expected_artifacts:
        errors.append("final comparison artifact set mismatch")
    for name, spec in artifacts.items():
        path = Path(spec.get("path", ""))
        if not path.is_file() or sha256(path) != spec.get("sha256"):
            errors.append(f"final comparison artifact missing/hash mismatch: {name}")

    benchmark_paths = {
        "flux2-a-direct": out / "flux2-a" / "source-aligned-direct-key" / "frozen-benchmark-report.json",
        "flux2-a": out / "flux2-a" / "source-payload-hybrid" / "frozen-benchmark-report.json",
        "nano-a-direct": out / "nano-a" / "source-aligned-direct-key" / "frozen-benchmark-report.json",
        "nano-a": out / "nano-a" / "source-payload-hybrid" / "frozen-benchmark-report.json",
        "assisted-r110": out / "assisted-r110-frozen-benchmark-report.json",
    }
    for name, path in benchmark_paths.items():
        if not path.is_file():
            errors.append(f"{name} frozen benchmark report missing")
            continue
        report = json.loads(path.read_text())
        case = report.get("reports", [{}])[0]
        codes = [failure.get("code") for failure in case.get("failures", [])]
        if report.get("machine_pass") is not False or case.get("final_verdict") != "FAIL":
            errors.append(f"{name} frozen benchmark was not recorded as rejected")
        if codes != EXPECTED_BENCHMARK_FAILURES[name]:
            errors.append(f"{name} frozen benchmark failure codes drifted: {codes}")

    evaluation_path = HERE / "EVALUATION.md"
    if not evaluation_path.is_file():
        errors.append("missing EVALUATION.md")
    else:
        evaluation = evaluation_path.read_text()
        evaluation_record = final.get("evaluation_report", {})
        if evaluation_record.get("path") != str(evaluation_path) or evaluation_record.get("sha256") != sha256(evaluation_path):
            errors.append("EVALUATION.md manifest lineage missing/hash mismatch")
        if "STATUS: COMPLETE — ALL CANDIDATES REJECTED" not in evaluation or "READY FOR JUDGING" not in evaluation:
            errors.append("EVALUATION.md closeout markers missing")
    return errors


def self_test() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        out = Path(temporary)
        (out / "manifest.json").write_text(json.dumps({
            "new_candidates": [{"id": "openai-a"}] * 5,
            "terminal_new_candidate_count": 5,
            "valid_new_candidate_count": 5,
        }))
        errors = validate(out)
        if not any("IDs/count mismatch" in error or "exactly four" in error for error in errors):
            raise SystemExit("negative_fixture_rejected=FAIL")
    print("negative_fixture_rejected=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.output is None:
        parser.error("output is required unless --self-test is used")
    errors = validate(args.output)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        raise SystemExit(1)
    print("candidate_count=4 PASS")
    print("source_reference_all=PASS")
    print("prompt_families_and_hashes=PASS")
    print("same_new_key_color=PASS")
    print("native_lineage=PASS")
    print("rgb_only_key_and_bounded_despill=PASS")
    print("all_review_artifacts=PASS")
    print("source_payload_hybrid_lineage=PASS")
    print("frozen_benchmark_rejections_recorded=PASS")
    print("final_comparison_and_evaluation=PASS")
    print("redaction=PASS")


if __name__ == "__main__":
    main()
