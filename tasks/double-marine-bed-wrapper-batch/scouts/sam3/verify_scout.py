#!/usr/bin/env python3
"""Structural verifier for the one-request SAM 3 scout.

Visual and semantic usefulness remain a separate verifier's responsibility.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

EXPECTED_SOURCE_SHA = "925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d"
EXPECTED_SIZE = (941, 1672)
EXPECTED_PROMPT = (
    "the complete watercolor marine illustration, including every coral, "
    "seaweed, fish, shell, bubble, rock, sandy seabed, and pale painted "
    "watercolor wash; exclude only blank white paper"
)
REQUIRED_FLAGS = {
    "return_multiple_masks": True,
    "max_masks": 32,
    "include_scores": True,
    "include_boxes": True,
    "apply_mask": False,
    "output_format": "png",
}
FORBIDDEN_TEXT = re.compile(r"(?i)(FAL_KEY|Authorization|data:image/|https?://[^\s\"]*fal\.(?:media|run))")


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def validate(out: Path) -> list[str]:
    errors = []
    attempt_path = out / "request-attempt.json"
    response_path = out / "response-summary.json"
    build_path = out / "build-summary.json"
    for path in (attempt_path, response_path, build_path):
        if not path.exists():
            errors.append(f"missing {path.name}")
    if errors:
        return errors
    attempt = json.loads(attempt_path.read_text())
    response = json.loads(response_path.read_text())
    build = json.loads(build_path.read_text())

    if attempt.get("request_count") != 1:
        errors.append(f"request_count must equal 1, got {attempt.get('request_count')!r}")
    if attempt.get("status") != "succeeded":
        errors.append(f"request status is {attempt.get('status')!r}")
    if attempt.get("endpoint") != "fal-ai/sam-3/image":
        errors.append("wrong endpoint")
    if attempt.get("prompt") != EXPECTED_PROMPT:
        errors.append("wrong semantic prompt")
    if attempt.get("arguments_without_image_url") != REQUIRED_FLAGS | {"prompt": EXPECTED_PROMPT}:
        errors.append("request flags or prompt recording mismatch")
    if attempt.get("source_sha256") != EXPECTED_SOURCE_SHA or tuple(attempt.get("source_size", [])) != EXPECTED_SIZE:
        errors.append("source identity mismatch")

    mask_count = response.get("mask_count")
    masks = response.get("masks", [])
    if not isinstance(mask_count, int) or mask_count < 1 or len(masks) != mask_count:
        errors.append("mask count is empty or inconsistent")
    for index, record in enumerate(masks):
        if record.get("index") != index:
            errors.append(f"mask index mismatch at {index}")
            continue
        path = out / record.get("local_path", "")
        if not path.is_file():
            errors.append(f"missing raw mask {index}")
        elif file_sha(path) != record.get("sha256"):
            errors.append(f"raw mask hash mismatch {index}")

    selected = build.get("selected_mask_indices", [])
    if not selected or any(not isinstance(i, int) or i < 0 or i >= (mask_count or 0) for i in selected):
        errors.append("invalid selected mask lineage")
    if build.get("held_out_benchmark_used_for_selection") is not False:
        errors.append("held-out benchmark use was not denied")
    if "bg-benchmark" in json.dumps(build).lower():
        errors.append("held-out benchmark path leaked into selection record")

    required_images = [
        "union-mask.png",
        "union-overlay.png",
        "alpha-cutout.png",
        "review-gray.png",
        "review-black.png",
        "review-magenta.png",
        "review-white.png",
        "per-mask-contact-sheet.png",
        "roi-cutout_01.png",
        "roi-cutout_02.png",
        "roi-fringe_00.png",
        "roi-outer_soft.png",
        "roi-enclosed_pocket.png",
        "roi-sand_base.png",
    ]
    for name in required_images:
        if not (out / name).is_file():
            errors.append(f"missing artifact {name}")
    for name in required_images[0:7]:
        path = out / name
        if path.is_file():
            with Image.open(path) as image:
                if image.size != EXPECTED_SIZE:
                    errors.append(f"{name} has size {image.size}, expected {EXPECTED_SIZE}")
    if (out / "union-mask.png").is_file() and (out / "alpha-cutout.png").is_file():
        with Image.open(out / "union-mask.png") as union_image, Image.open(out / "alpha-cutout.png") as rgba_image:
            union = np.asarray(union_image.convert("L"))
            alpha = np.asarray(rgba_image.getchannel("A"))
            if not np.array_equal(union, alpha):
                errors.append("alpha cutout alpha differs from union mask")

    for path in (attempt_path, response_path, build_path, out / "mask-inspection-metadata.json"):
        if path.exists() and FORBIDDEN_TEXT.search(path.read_text()):
            errors.append(f"unredacted key/data URI/provider URL in {path.name}")
    return errors


def self_test() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        out = Path(temporary)
        (out / "request-attempt.json").write_text(json.dumps({"request_count": 2}))
        (out / "response-summary.json").write_text("{}")
        (out / "build-summary.json").write_text("{}")
        errors = validate(out)
        if not any("request_count must equal 1" in error for error in errors):
            raise SystemExit("NEGATIVE_FIXTURE_REJECTED=FAIL")
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
    print("request_count=1")
    print("request_flags=PASS")
    print("all_masks_downloaded=PASS")
    print("union_lineage=PASS")
    print("native_artifacts=PASS")
    print("alpha_identity=PASS")
    print("redaction=PASS")


if __name__ == "__main__":
    main()
