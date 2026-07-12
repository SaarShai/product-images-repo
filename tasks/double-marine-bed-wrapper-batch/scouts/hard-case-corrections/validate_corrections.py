#!/usr/bin/env python3
"""Fresh structural validation and metrics for sparse correction overlays."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
HERE = Path(__file__).resolve().parent
RED = np.array([255, 0, 0, 255], dtype=np.uint8)
BLUE = np.array([0, 0, 255, 255], dtype=np.uint8)

CASES = {
    "image15": {
        "source": PRODUCT / "ChatGPT Image Jul 7, 2026, 11_34_15 AM.png",
        "expected_source_sha256": "bf6f2deb7bce6e2b76a644d0caa7e3ae6519837c4d0842d47c548bc4fb650e72",
        "candidate": PRODUCT
        / "Images/candidates/bg-assisted-v2/image15/auto-proposal-v1/"
        "image15-auto-v1-rgba.png",
        "overlay": PRODUCT
        / "Images/candidates/bg-assisted-v2/image15/corrections-v1/"
        "image15-corrections-v1-rgba.png",
    },
    "sample08": {
        "source": PRODUCT / "ChatGPT Image Jul 7, 2026, 11_09_25 AM.png",
        "expected_source_sha256": "8b0111dab8fb19887a83b8aaf8c6140e89d1b3e93b8b61265ab94e6ac3416af2",
        "candidate": PRODUCT
        / "Images/candidates/bg-assisted-v2/sample08/auto-proposal-v1/"
        "sample08-auto-v1-rgba.png",
        "overlay": PRODUCT
        / "Images/candidates/bg-assisted-v2/sample08/corrections-v1/"
        "sample08-corrections-v1-rgba.png",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pixel_errors(array: np.ndarray) -> list[str]:
    alpha = array[..., 3]
    opaque = alpha == 255
    transparent = alpha == 0
    red = np.all(array == RED, axis=2)
    blue = np.all(array == BLUE, axis=2)
    errors = []
    if not np.all(opaque | transparent):
        errors.append("partial_alpha")
    if not np.all(~opaque | red | blue):
        errors.append("invalid_label_colors")
    if not np.all(~transparent | np.all(array == 0, axis=2)):
        errors.append("nonzero_rgb_under_alpha0")
    if np.any(red & blue):
        errors.append("red_blue_overlap")
    return errors


def analyze(case: str, spec: dict) -> dict:
    source = Image.open(spec["source"])
    candidate = Image.open(spec["candidate"]).convert("RGBA")
    overlay_image = Image.open(spec["overlay"])
    overlay = np.asarray(overlay_image)
    candidate_alpha = np.asarray(candidate.getchannel("A"))
    errors = pixel_errors(overlay)
    if overlay_image.mode != "RGBA":
        errors.append("overlay_not_rgba")
    if overlay_image.size != source.size:
        errors.append("overlay_source_dimension_mismatch")
    if candidate.size != source.size:
        errors.append("candidate_source_dimension_mismatch")
    source_hash = sha256(spec["source"])
    if source_hash != spec["expected_source_sha256"]:
        errors.append("source_hash_changed")

    red = np.all(overlay == RED, axis=2)
    blue = np.all(overlay == BLUE, axis=2)
    labeled = red | blue
    red_on_removed = float(np.mean(candidate_alpha[red] < 64)) if np.any(red) else None
    blue_on_retained = float(np.mean(candidate_alpha[blue] >= 192)) if np.any(blue) else None

    # Sparse correction strokes should occupy much less than a full mask.
    label_fraction = float(np.mean(labeled))
    if label_fraction >= 0.01:
        errors.append("overlay_not_sparse")
    if np.any(red) and red_on_removed < 0.70:
        errors.append("red_not_concentrated_on_candidate_false_negatives")

    return {
        "case": case,
        "source": str(spec["source"]),
        "candidate": str(spec["candidate"]),
        "overlay": str(spec["overlay"]),
        "source_dimensions": list(source.size),
        "overlay_dimensions": list(overlay_image.size),
        "overlay_mode": overlay_image.mode,
        "source_sha256": source_hash,
        "source_hash_unchanged": source_hash == spec["expected_source_sha256"],
        "overlay_sha256": sha256(spec["overlay"]),
        "red_pixels": int(np.count_nonzero(red)),
        "blue_pixels": int(np.count_nonzero(blue)),
        "unknown_pixels": int(np.count_nonzero(overlay[..., 3] == 0)),
        "partial_alpha_pixels": int(np.count_nonzero((overlay[..., 3] > 0) & (overlay[..., 3] < 255))),
        "label_fraction": label_fraction,
        "red_on_candidate_alpha_lt_64_fraction": red_on_removed,
        "blue_on_candidate_alpha_gte_192_fraction": blue_on_retained,
        "errors": errors,
        "passed": not errors,
    }


def main() -> None:
    # Negative fixture: the gate must reject an opaque color other than red/blue.
    invalid = np.array([[[1, 2, 3, 255]]], dtype=np.uint8)
    negative_errors = pixel_errors(invalid)
    if "invalid_label_colors" not in negative_errors:
        raise AssertionError("negative fixture did not trip invalid_label_colors")

    metrics = {
        "negative_fixture": {
            "input_rgba": [1, 2, 3, 255],
            "expected_error": "invalid_label_colors",
            "observed_errors": negative_errors,
            "passed": True,
        },
        "cases": {case: analyze(case, spec) for case, spec in CASES.items()},
    }
    metrics["passed"] = all(item["passed"] for item in metrics["cases"].values())
    (HERE / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    for case, item in metrics["cases"].items():
        print(
            f"{case}: passed={item['passed']} dims={item['overlay_dimensions']} "
            f"mode={item['overlay_mode']} red={item['red_pixels']} "
            f"blue={item['blue_pixels']} label_fraction={item['label_fraction']:.6f} "
            f"red_on_removed={item['red_on_candidate_alpha_lt_64_fraction']} "
            f"source_hash_unchanged={item['source_hash_unchanged']} errors={item['errors']}"
        )
    print(f"negative_fixture_passed={metrics['negative_fixture']['passed']}")
    print(f"overall_passed={metrics['passed']}")
    if not metrics["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
