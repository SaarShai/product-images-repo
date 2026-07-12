#!/usr/bin/env python3
"""Mechanical evidence gate for the bounded transparency/upscale scout."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


REPO = Path(__file__).resolve().parents[4]
PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
OUT = PRODUCT / "Images/candidates/openai-transparent-image14"
SOURCE = PRODUCT / "ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
SOURCE_SHA = "925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_rgba_soft(path: Path, size: tuple[int, int]) -> None:
    image = Image.open(path)
    assert image.mode == "RGBA", f"{path.name}: {image.mode}"
    assert image.size == size, f"{path.name}: {image.size}"
    alpha = np.asarray(image.getchannel("A"))
    assert int(alpha.min()) == 0 and int(alpha.max()) == 255
    assert np.any((alpha > 0) & (alpha < 255)), f"{path.name}: hardened alpha"
    assert np.isfinite(np.asarray(image.convert("RGB"))).all()
    assert "finals" not in {part.lower() for part in path.resolve().parts}


def verify_metric_order(metrics: dict[str, object]) -> None:
    synth = metrics["synthetic_known_alpha"]
    synth_direct = synth["direct"]["vs_split_oracle"]
    synth_two = synth["two_plate"]["vs_split_oracle"]
    assert synth_direct["alpha_mae_0_255"] < synth_two["alpha_mae_0_255"], (
        "expected direct synthetic alpha error below nonlinear two-plate error"
    )
    real = metrics["real_r110_control_crop"]
    direct_edge = real["direct"]["vs_split_reference"]["soft_edge_composite_mae_0_255"]
    two_edge = real["two_plate"]["vs_split_reference"]["soft_edge_composite_mae_0_255"]
    assert direct_edge["black"] < two_edge["black"]
    assert direct_edge["magenta"] < two_edge["magenta"]


def verify() -> None:
    assert sha256(SOURCE) == SOURCE_SHA, "authoritative source changed"
    call_metrics = json.loads((OUT / "openai-call-metrics.json").read_text(encoding="utf-8"))
    assert call_metrics["actual_openai_image_call_count"] == 2
    assert call_metrics["call_budget_exhausted"] is True
    assert len(list(OUT.glob("call*.png"))) == 2
    expected_calls = [((940, 1673), "RGB"), ((941, 1672), "RGB")]
    for record, (size, mode) in zip(call_metrics["calls"], expected_calls):
        assert tuple(record["size"]) == size
        assert record["mode"] == mode
        assert record["genuine_alpha"] is False

    probe = json.loads((OUT / "ncnn-rgba-probe/probe-metrics.json").read_text(encoding="utf-8"))
    assert probe["probe_count"] == 1
    assert probe["returncode"] == 0
    assert probe["output"]["mode"] == "RGBA"
    assert probe["output"]["size"] == [256, 256]

    for method in ("split", "direct", "two-plate"):
        assert_rgba_soft(OUT / f"upscale-comparison/r110-crop-{method}-x8.png", (1920, 1920))
        assert_rgba_soft(OUT / f"synthetic-comparison/synthetic-{method}-x8.png", (512, 512))
    metrics = json.loads((OUT / "upscale-comparison-metrics.json").read_text(encoding="utf-8"))
    verify_metric_order(metrics)

    required_boards = [
        OUT / "openai-call-comparison-board.jpg",
        OUT / "synthetic-comparison/direct-vs-split-vs-two-plate-board.png",
        OUT / "synthetic-comparison/alpha-board.png",
        OUT / "upscale-comparison/direct-vs-split-vs-two-plate-board.png",
        OUT / "upscale-comparison/alpha-board.png",
    ]
    assert all(path.is_file() and path.stat().st_size > 8000 for path in required_boards)
    assert (OUT / "README.md").is_file()
    assert (REPO / "tasks/double-marine-bed-wrapper-batch/alpha_aware_upscale.py").is_file()
    assert (REPO / "tasks/double-marine-bed-wrapper-batch/tests/test_alpha_aware_upscale.py").is_file()
    print(
        "PASS source_sha=true openai_calls=2 opaque_calls=2 ncnn_rgba_probe=1 "
        "real_x8_rgba=3 synthetic_x8_rgba=3 soft_alpha=true boards=5 "
        "direct_error_lt_two_plate=true finals=0"
    )


def negative_fixture() -> None:
    metrics = json.loads((OUT / "upscale-comparison-metrics.json").read_text(encoding="utf-8"))
    broken = copy.deepcopy(metrics)
    broken["synthetic_known_alpha"]["two_plate"]["vs_split_oracle"]["alpha_mae_0_255"] = 0.0
    try:
        verify_metric_order(broken)
    except AssertionError:
        print("NEGATIVE PASS metric-order gate rejected falsified two-plate superiority")
        return
    raise AssertionError("negative fixture did not trip")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--negative-fixture", action="store_true")
    args = parser.parse_args()
    if args.negative_fixture:
        negative_fixture()
    else:
        verify()


if __name__ == "__main__":
    main()
