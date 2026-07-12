#!/usr/bin/env python3
"""Mechanical shape/lineage verifier for the one-shot ViTMatte scout."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image


OUT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/image14-research/"
    "vitmatte-scout"
)
SOURCE = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
)


def main() -> None:
    required = [
        "14-vitmatte-scout-source-rgb.png",
        "14-vitmatte-scout-recovered-rgb.png",
        "14-vitmatte-scout-alpha.png",
        "14-vitmatte-scout-trimap.png",
        "14-vitmatte-scout-seed-alpha-native.png",
        "review-cutout_01-four-backgrounds.png",
        "review-cutout_02-four-backgrounds.png",
        "review-fringe_00-four-backgrounds.png",
        "review-outer_soft-four-backgrounds.png",
        "review-full-gray-black-source-vs-recovered.png",
        "README.md",
        "metrics.json",
    ]
    missing = [name for name in required if not (OUT / name).is_file()]
    assert not missing, f"missing outputs: {missing}"

    source = Image.open(OUT / required[0])
    recovered = Image.open(OUT / required[1])
    assert source.mode == recovered.mode == "RGBA"
    assert source.size == recovered.size == (941, 1672)
    source_alpha = np.asarray(source.getchannel("A"))
    recovered_alpha = np.asarray(recovered.getchannel("A"))
    source_rgb = np.asarray(source.convert("RGB"))
    recovered_rgb = np.asarray(recovered.convert("RGB"))
    original_rgb = np.asarray(Image.open(SOURCE).convert("RGB"))
    assert np.array_equal(source_alpha, recovered_alpha), "RGBA alpha mismatch"
    assert np.any((source_alpha > 0) & (source_alpha < 255)), "alpha was hardened"
    assert np.array_equal(source_rgb, original_rgb), "source-RGB payload changed"
    assert not np.array_equal(recovered_rgb, source_rgb), "foreground recovery did not change RGB"
    assert np.any(source_rgb[source_alpha == 0] != 0), "source payload appears premultiplied"

    trimap = np.asarray(Image.open(OUT / "14-vitmatte-scout-trimap.png"))
    assert set(np.unique(trimap).tolist()) == {0, 128, 255}

    metrics = json.loads((OUT / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["inputs"]["source_size_wh"] == [941, 1672]
    assert metrics["run"]["source_shape_hw"] == [1672, 941]
    assert metrics["run"]["processor_pixel_values_shape"] == [1, 4, 1696, 960]
    assert metrics["rgba_alpha_identical"] is True
    assert metrics["trimap"]["not_ground_truth"] is True
    assert metrics["run"]["device_requested"] == "mps"
    assert metrics["run"]["device_used"] == "mps"
    assert metrics["run"]["mps_fallback_error"] is None
    assert metrics["run"]["forward_seconds"] > 0
    assert metrics["alpha"]["soft_pct"] > 0
    assert set(metrics["roi_metrics"]) == {"cutout_01", "cutout_02", "fringe_00", "outer_soft"}
    print(
        "PASS files=12 rgba=941x1672 source_rgb_exact=true recovered_rgb_distinct=true "
        "alpha_identical=true alpha_soft=true straight_rgba=true trimap_values=0,128,255 "
        f"device={metrics['run']['device_used']} padded=1696x960 rois=4"
    )


if __name__ == "__main__":
    main()
