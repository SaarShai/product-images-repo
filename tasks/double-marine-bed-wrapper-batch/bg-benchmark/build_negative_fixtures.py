#!/usr/bin/env python3
"""Build deterministic positive and negative fixtures for the BG verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np
from PIL import Image


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def composite(rgb: np.ndarray, alpha: np.ndarray, background: np.ndarray) -> np.ndarray:
    alpha32 = alpha.astype(np.uint32)[:, :, None]
    return (
        (
            rgb.astype(np.uint32) * alpha32
            + background.astype(np.uint32)[None, None, :] * (255 - alpha32)
            + 127
        )
        // 255
    ).astype(np.uint8)


def rgba_image(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    return np.dstack([rgb, alpha]).astype(np.uint8)


def disk(xx: np.ndarray, yy: np.ndarray, x: float, y: float, radius: float) -> np.ndarray:
    return (xx - x) ** 2 + (yy - y) ** 2 <= radius**2


def build_fixture_set(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = output_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)

    width = height = 64
    yy, xx = np.ogrid[:height, :width]
    core = disk(xx, yy, 30, 32, 13)
    soft_ring = disk(xx, yy, 30, 32, 16) & ~core
    enclosed_hole = disk(xx, yy, 30, 32, 5)
    appendage = (xx >= 43) & (xx <= 57) & (yy >= 28) & (yy <= 36)

    alpha = np.zeros((height, width), dtype=np.uint8)
    alpha[core] = 255
    alpha[soft_ring] = 128
    alpha[appendage] = 180
    alpha[enclosed_hole] = 0

    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[:, :] = (70, 115, 180)
    rgb[appendage] = (230, 150, 120)
    paper = np.array([255, 255, 255], dtype=np.uint8)
    source = composite(rgb, alpha, paper)

    source_path = output_dir / "source.png"
    Image.fromarray(source).save(source_path)

    annotations = {
        "schema_version": 1,
        "case_id": "synthetic",
        "coordinate_space": {
            "reference": "original",
            "width": width,
            "height": height,
            "origin": "top_left",
            "units": "pixels",
        },
        "provenance": {
            "method": "synthetic_ground_truth",
            "candidate_independent": True,
            "note": "Guards are defined from the fixture construction, not recovered from candidates.",
        },
        "sure_foreground": [
            {
                "id": "fg-painted-core",
                "center": [20, 32],
                "radius": 2,
                "alpha_min": 200,
                "min_fraction": 0.9,
                "median_min": 220,
            },
            {
                "id": "fg-pale-appendage",
                "center": [50, 32],
                "radius": 2,
                "alpha_min": 128,
                "min_fraction": 0.9,
                "median_min": 160,
            },
        ],
        "sure_background_exterior": [
            {"id": "bg-exterior", "center": [4, 4], "radius": 2, "alpha_max": 16, "min_fraction": 1.0}
        ],
        "sure_background_enclosed": [
            {"id": "bg-enclosed-hole", "center": [30, 32], "radius": 2, "alpha_max": 16, "min_fraction": 1.0}
        ],
        "edge_probes": [
            {
                "id": "edge-painted-shape",
                "bbox": [8, 12, 60, 52],
                "band_width": 1,
                "paper_distance_min": 10,
                "max_white_fraction": 0.05,
                "min_boundary_pixels_per_scale": 10,
            }
        ],
        "human_review": [],
    }
    annotations_path = output_dir / "annotations.json"
    annotations_path.write_text(json.dumps(annotations, indent=2) + "\n", encoding="utf-8")

    candidates: Dict[str, np.ndarray] = {"good": rgba_image(rgb, alpha)}

    white_fringe = candidates["good"].copy()
    fringe = disk(xx, yy, 30, 32, 18) & ~disk(xx, yy, 30, 32, 16) & ~appendage
    white_fringe[fringe, :3] = 255
    white_fringe[fringe, 3] = 255
    candidates["negative-white-fringe"] = white_fringe

    deleted_foreground = candidates["good"].copy()
    deleted = disk(xx, yy, 20, 32, 3)
    deleted_foreground[deleted, 3] = 0
    candidates["negative-deleted-foreground"] = deleted_foreground

    retained_enclosed = candidates["good"].copy()
    retained_enclosed[enclosed_hole, :3] = 255
    retained_enclosed[enclosed_hole, 3] = 255
    candidates["negative-retained-enclosed-bg"] = retained_enclosed

    degenerate_alpha = np.dstack([source, np.full((height, width), 255, dtype=np.uint8)])
    candidates["negative-degenerate-alpha"] = degenerate_alpha

    premultiplied = candidates["good"].copy()
    partial = (premultiplied[:, :, 3] > 0) & (premultiplied[:, :, 3] < 255)
    premultiplied[partial, :3] = (
        premultiplied[partial, :3].astype(np.uint16)
        * premultiplied[partial, 3:4].astype(np.uint16)
        // 255
    ).astype(np.uint8)
    candidates["negative-premultiplied-rgb"] = premultiplied

    candidate_paths: Dict[str, Path] = {}
    for name, rgba in candidates.items():
        path = candidate_dir / f"{name}.png"
        Image.fromarray(rgba).save(path)
        candidate_paths[name] = path

    bad_dimensions_path = candidate_dir / "negative-bad-dimensions.png"
    Image.fromarray(candidates["good"][:, :-1]).save(bad_dimensions_path)
    candidate_paths["negative-bad-dimensions"] = bad_dimensions_path

    missing_alpha_path = candidate_dir / "negative-missing-alpha.png"
    Image.fromarray(source).save(missing_alpha_path)
    candidate_paths["negative-missing-alpha"] = missing_alpha_path

    wrong_format_path = candidate_dir / "negative-wrong-format.tiff"
    Image.fromarray(candidates["good"]).save(wrong_format_path)
    candidate_paths["negative-wrong-format"] = wrong_format_path

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

    asset = {
        "base": "manifest",
        "path": source_path.name,
        "sha256": sha256_file(source_path),
        "width": width,
        "height": height,
    }
    cases = []
    for name, path in candidate_paths.items():
        cases.append(
            {
                "id": name,
                "status": "ready",
                "original": dict(asset),
                "references": [{**asset, "scale": 1}],
                "annotations": {"base": "manifest", "path": annotations_path.name},
                "candidate": {"base": "manifest", "path": str(path.relative_to(output_dir))},
                "expected_failure_codes": expected[name],
            }
        )

    manifest: Dict[str, Any] = {
        "schema_version": 1,
        "benchmark_id": "synthetic-bg-negative-controls-v1",
        "contract": {
            "paper_rgb": [255, 255, 255],
            "alpha_background_max": 16,
            "alpha_foreground_min": 96,
            "min_background_fraction": 0.15,
            "min_foreground_fraction": 0.05,
            "reconstruction_mae_max": 0.0,
            "reconstruction_p99_max": 0,
            "composite_backgrounds": {
                "white": [255, 255, 255],
                "gray": [140, 140, 140],
                "black": [0, 0, 0],
                "magenta": [255, 0, 255],
            },
        },
        "cases": cases,
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = build_fixture_set(args.output_dir.expanduser().resolve())
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
