#!/usr/bin/env python3
"""Independent verifier for transparent watercolor background removal.

The verifier consumes source-authored sparse guards. It never derives semantic
truth from the candidate under test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw


Image.MAX_IMAGE_PIXELS = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_paper_rgb(
    case: Mapping[str, Any],
    annotations: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> Tuple[List[int], str]:
    case_value = case.get("paper_rgb")
    annotation_value = annotations.get("paper_rgb")
    if case_value is not None and annotation_value is not None and case_value != annotation_value:
        raise ValueError("case and annotation paper_rgb values disagree")

    if case_value is not None:
        raw, source = case_value, "case"
    elif annotation_value is not None:
        raw, source = annotation_value, "annotation"
    else:
        raw, source = contract.get("paper_rgb", [255, 255, 255]), "contract"

    if not isinstance(raw, (list, tuple)) or len(raw) != 3:
        raise ValueError(f"paper_rgb must be a three-item RGB list, got {raw!r}")
    parsed: List[int] = []
    for value in raw:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"paper_rgb channels must be numeric, got {raw!r}")
        channel = int(value)
        if channel != value or not 0 <= channel <= 255:
            raise ValueError(f"paper_rgb channels must be integers from 0 to 255, got {raw!r}")
        parsed.append(channel)
    return parsed, source


def resolve_path(
    spec: Mapping[str, Any], manifest_dir: Path, product_root: Optional[Path]
) -> Path:
    raw = Path(str(spec["path"])).expanduser()
    if raw.is_absolute():
        return raw
    base = str(spec.get("base", "manifest"))
    if base == "manifest":
        return (manifest_dir / raw).resolve()
    if base == "product_root":
        if product_root is None:
            raise ValueError(f"path requests product_root but manifest has none: {raw}")
        return (product_root / raw).resolve()
    raise ValueError(f"unsupported path base {base!r} for {raw}")


def failure(code: str, message: str, **details: Any) -> Dict[str, Any]:
    item: Dict[str, Any] = {"code": code, "message": message}
    if details:
        item["details"] = details
    return item


def validate_asset(
    spec: Mapping[str, Any],
    manifest_dir: Path,
    product_root: Optional[Path],
    label: str,
    failures: List[Dict[str, Any]],
) -> Optional[Path]:
    try:
        path = resolve_path(spec, manifest_dir, product_root)
    except (KeyError, ValueError) as exc:
        failures.append(failure("asset_spec_invalid", f"{label}: {exc}"))
        return None
    if not path.is_file():
        failures.append(failure("asset_missing", f"{label} missing: {path}", path=str(path)))
        return None

    expected_hash = spec.get("sha256")
    if expected_hash:
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            failures.append(
                failure(
                    "source_identity_mismatch",
                    f"{label} SHA-256 mismatch",
                    path=str(path),
                    expected=expected_hash,
                    actual=actual_hash,
                )
            )

    try:
        with Image.open(path) as image:
            actual_size = [image.width, image.height]
    except OSError as exc:
        failures.append(failure("asset_unreadable", f"{label} unreadable: {exc}", path=str(path)))
        return None

    expected_size = [int(spec.get("width", -1)), int(spec.get("height", -1))]
    if expected_size[0] > 0 and actual_size != expected_size:
        failures.append(
            failure(
                "source_dimension_mismatch",
                f"{label} dimensions changed",
                path=str(path),
                expected=expected_size,
                actual=actual_size,
            )
        )
    return path


def percentile_from_histogram(histogram: np.ndarray, percentile: float) -> int:
    total = int(histogram.sum())
    if total == 0:
        return 0
    target = max(1, int(math.ceil(total * percentile / 100.0)))
    return int(np.searchsorted(np.cumsum(histogram), target, side="left"))


def composite_chunk(rgb: np.ndarray, alpha: np.ndarray, background: Sequence[int]) -> np.ndarray:
    rgb32 = rgb.astype(np.uint32)
    alpha32 = alpha.astype(np.uint32)[:, :, None]
    bg32 = np.asarray(background, dtype=np.uint32)[None, None, :]
    return ((rgb32 * alpha32 + bg32 * (255 - alpha32) + 127) // 255).astype(np.uint8)


def scan_reconstruction_and_composites(
    candidate: Image.Image,
    reference: Image.Image,
    paper_rgb: Sequence[int],
    backgrounds: Mapping[str, Sequence[int]],
    chunk_rows: int = 256,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    diff_hist = np.zeros(256, dtype=np.int64)
    diff_sum = 0
    diff_count = 0
    diff_max = 0

    composite_hashers = {name: hashlib.sha256() for name in backgrounds}
    composite_sums = {name: np.zeros(3, dtype=np.uint64) for name in backgrounds}
    composite_pixels = 0

    for y0 in range(0, candidate.height, chunk_rows):
        y1 = min(candidate.height, y0 + chunk_rows)
        rgba = np.asarray(candidate.crop((0, y0, candidate.width, y1)).convert("RGBA"), dtype=np.uint8)
        ref = np.asarray(reference.crop((0, y0, reference.width, y1)).convert("RGB"), dtype=np.uint8)
        rgb = rgba[:, :, :3]
        alpha = rgba[:, :, 3]

        reconstructed = composite_chunk(rgb, alpha, paper_rgb)
        diff = np.abs(reconstructed.astype(np.int16) - ref.astype(np.int16)).astype(np.uint8)
        diff_hist += np.bincount(diff.ravel(), minlength=256)
        diff_sum += int(diff.sum(dtype=np.uint64))
        diff_count += int(diff.size)
        diff_max = max(diff_max, int(diff.max(initial=0)))

        for name, background in backgrounds.items():
            comp = composite_chunk(rgb, alpha, background)
            composite_hashers[name].update(comp.tobytes(order="C"))
            composite_sums[name] += comp.sum(axis=(0, 1), dtype=np.uint64)
        composite_pixels += int(alpha.size)

    reconstruction = {
        "mae": float(diff_sum / max(1, diff_count)),
        "p95": percentile_from_histogram(diff_hist, 95.0),
        "p99": percentile_from_histogram(diff_hist, 99.0),
        "max": diff_max,
    }
    composites = {
        name: {
            "sha256_rgb_bytes": composite_hashers[name].hexdigest(),
            "mean_rgb": [float(value / max(1, composite_pixels)) for value in composite_sums[name]],
            "width": candidate.width,
            "height": candidate.height,
        }
        for name in backgrounds
    }
    return reconstruction, composites


def scaled_center(center: Sequence[float], scale: float) -> Tuple[float, float]:
    return ((float(center[0]) + 0.5) * scale - 0.5, (float(center[1]) + 0.5) * scale - 0.5)


def sample_disk(alpha: Image.Image, center: Sequence[float], radius: float, scale: float) -> np.ndarray:
    cx, cy = scaled_center(center, scale)
    radius_scaled = max(1.0, float(radius) * scale)
    x0 = max(0, int(math.floor(cx - radius_scaled)))
    y0 = max(0, int(math.floor(cy - radius_scaled)))
    x1 = min(alpha.width, int(math.ceil(cx + radius_scaled)) + 1)
    y1 = min(alpha.height, int(math.ceil(cy + radius_scaled)) + 1)
    patch = np.asarray(alpha.crop((x0, y0, x1, y1)), dtype=np.uint8)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius_scaled**2
    return patch[disk]


def check_guards(
    alpha: Image.Image,
    annotations: Mapping[str, Any],
    scale: float,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    failures: List[Dict[str, Any]] = []
    metrics: List[Dict[str, Any]] = []

    groups = (
        ("sure_foreground", "deleted_foreground"),
        ("sure_background_exterior", "exterior_background_retained"),
        ("sure_background_enclosed", "enclosed_background_retained"),
    )
    for group_name, failure_code in groups:
        for guard in annotations.get(group_name, []):
            values = sample_disk(alpha, guard["center"], float(guard.get("radius", 1)), scale)
            if values.size == 0:
                failures.append(failure("guard_out_of_bounds", f"{guard['id']} sampled no pixels"))
                continue

            if group_name == "sure_foreground":
                threshold = int(guard.get("alpha_min", 96))
                fraction = float((values >= threshold).mean())
                median = float(np.median(values))
                required_fraction = float(guard.get("min_fraction", 0.8))
                required_median = float(guard.get("median_min", threshold))
                passed = fraction >= required_fraction and median >= required_median
                metric = {
                    "id": guard["id"],
                    "group": group_name,
                    "alpha_threshold": threshold,
                    "fraction_meeting_threshold": fraction,
                    "required_fraction": required_fraction,
                    "median_alpha": median,
                    "required_median": required_median,
                    "passed": passed,
                }
            else:
                threshold = int(guard.get("alpha_max", 16))
                fraction = float((values <= threshold).mean())
                required_fraction = float(guard.get("min_fraction", 0.9))
                p90 = float(np.percentile(values, 90))
                passed = fraction >= required_fraction
                metric = {
                    "id": guard["id"],
                    "group": group_name,
                    "alpha_threshold": threshold,
                    "fraction_meeting_threshold": fraction,
                    "required_fraction": required_fraction,
                    "p90_alpha": p90,
                    "passed": passed,
                }
            metrics.append(metric)
            if not passed:
                failures.append(
                    failure(
                        failure_code,
                        f"guard {guard['id']} failed",
                        guard=guard["id"],
                        group=group_name,
                        metric=metric,
                    )
                )
    return failures, metrics


def dilate(mask: np.ndarray, iterations: int) -> np.ndarray:
    result = mask.astype(bool, copy=True)
    height, width = result.shape
    for _ in range(max(0, iterations)):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        neighbors = [
            padded[dy : dy + height, dx : dx + width]
            for dy in range(3)
            for dx in range(3)
        ]
        result = np.logical_or.reduce(neighbors)
    return result


def scaled_bbox(bbox: Sequence[float], scale: float) -> Tuple[int, int, int, int]:
    return (
        int(math.floor(float(bbox[0]) * scale)),
        int(math.floor(float(bbox[1]) * scale)),
        int(math.ceil(float(bbox[2]) * scale)),
        int(math.ceil(float(bbox[3]) * scale)),
    )


def check_edges(
    candidate: Image.Image,
    annotations: Mapping[str, Any],
    scale: float,
    paper_rgb: Sequence[int],
    alpha_background_max: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    failures: List[Dict[str, Any]] = []
    metrics: List[Dict[str, Any]] = []
    for probe in annotations.get("edge_probes", []):
        core_x0, core_y0, core_x1, core_y1 = scaled_bbox(probe["bbox"], scale)
        band_width = max(1, int(math.ceil(float(probe.get("band_width", 2)) * scale)))
        x0 = max(0, core_x0 - band_width - 1)
        y0 = max(0, core_y0 - band_width - 1)
        x1 = min(candidate.width, core_x1 + band_width + 1)
        y1 = min(candidate.height, core_y1 + band_width + 1)

        rgba = np.asarray(candidate.crop((x0, y0, x1, y1)).convert("RGBA"), dtype=np.uint8)
        alpha = rgba[:, :, 3]
        foreground = alpha > alpha_background_max
        boundary_band = foreground & dilate(~foreground, band_width)

        core = np.zeros_like(foreground, dtype=bool)
        core[
            max(0, core_y0 - y0) : min(core.shape[0], core_y1 - y0),
            max(0, core_x0 - x0) : min(core.shape[1], core_x1 - x0),
        ] = True
        boundary_band &= core

        boundary_count = int(boundary_band.sum())
        min_count = max(1, int(math.ceil(float(probe.get("min_boundary_pixels_per_scale", 4)) * scale)))
        if boundary_count < min_count:
            metric = {
                "id": probe["id"],
                "boundary_pixels": boundary_count,
                "required_boundary_pixels": min_count,
                "passed": False,
            }
            metrics.append(metric)
            failures.append(
                failure(
                    "edge_probe_empty",
                    f"edge probe {probe['id']} has too little foreground boundary",
                    probe=probe["id"],
                    metric=metric,
                )
            )
            continue

        rgb = rgba[:, :, :3].astype(np.int32)
        paper = np.asarray(paper_rgb, dtype=np.int32)[None, None, :]
        paper_distance = np.sqrt(((rgb - paper) ** 2).sum(axis=2))
        distance_min = float(probe.get("paper_distance_min", 10.0))
        near_paper = boundary_band & (paper_distance < distance_min)
        white_fraction = float(near_paper.sum() / boundary_count)
        max_fraction = float(probe.get("max_white_fraction", 0.15))
        passed = white_fraction <= max_fraction
        metric = {
            "id": probe["id"],
            "boundary_pixels": boundary_count,
            "paper_distance_min": distance_min,
            "near_paper_boundary_pixels": int(near_paper.sum()),
            "white_fraction": white_fraction,
            "max_white_fraction": max_fraction,
            "passed": passed,
        }
        metrics.append(metric)
        if not passed:
            failures.append(
                failure(
                    "white_edge_contamination",
                    f"edge probe {probe['id']} contains too many paper-colored boundary pixels",
                    probe=probe["id"],
                    metric=metric,
                )
            )
    return failures, metrics


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._") or "review"


def composite_image(rgba: np.ndarray, background: Sequence[int]) -> np.ndarray:
    return composite_chunk(rgba[:, :, :3], rgba[:, :, 3], background)


def write_review_board(
    candidate: Image.Image,
    bbox: Sequence[float],
    scale: float,
    backgrounds: Mapping[str, Sequence[int]],
    path: Path,
) -> None:
    x0, y0, x1, y1 = scaled_bbox(bbox, scale)
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(candidate.width, x1), min(candidate.height, y1)
    rgba = np.asarray(candidate.crop((x0, y0, x1, y1)).convert("RGBA"), dtype=np.uint8)
    panels = [(name, Image.fromarray(composite_image(rgba, color))) for name, color in backgrounds.items()]
    header_height = 24
    board = Image.new("RGB", (sum(panel.width for _, panel in panels), rgba.shape[0] + header_height), "white")
    draw = ImageDraw.Draw(board)
    offset = 0
    for name, panel in panels:
        board.paste(panel, (offset, header_height))
        draw.text((offset + 4, 4), name, fill="black")
        offset += panel.width
    path.parent.mkdir(parents=True, exist_ok=True)
    board.save(path, optimize=True)


def write_review_artifacts(
    original_path: Path,
    candidate: Image.Image,
    annotations: Mapping[str, Any],
    scale: float,
    backgrounds: Mapping[str, Sequence[int]],
    review_dir: Path,
    case_id: str,
) -> List[str]:
    overlay_path = review_dir / f"{safe_slug(case_id)}--source-annotation-overlay.png"
    write_annotation_overlay(original_path, annotations, overlay_path)
    artifacts: List[str] = [str(overlay_path)]
    seen: set = set()
    for probe in annotations.get("edge_probes", []):
        item = (probe["id"], tuple(probe["bbox"]))
        seen.add(item)
    for review in annotations.get("human_review", []):
        if review.get("kind") == "bbox":
            seen.add((review["id"], tuple(review["bbox"])))
    for review_id, bbox in sorted(seen):
        out = review_dir / f"{safe_slug(case_id)}--{safe_slug(str(review_id))}--white-gray-black-magenta.png"
        write_review_board(candidate, bbox, scale, backgrounds, out)
        artifacts.append(str(out))
    return artifacts


def write_annotation_overlay(
    original_path: Path, annotations: Mapping[str, Any], path: Path
) -> None:
    with Image.open(original_path) as source:
        preview = source.convert("RGB")
    draw = ImageDraw.Draw(preview)
    groups = (
        ("sure_foreground", (220, 20, 20)),
        ("sure_background_exterior", (25, 80, 230)),
        ("sure_background_enclosed", (0, 175, 210)),
    )
    for group_name, color in groups:
        for guard in annotations.get(group_name, []):
            x, y = guard["center"]
            radius = max(2, int(math.ceil(float(guard.get("radius", 1)))))
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=2)
            draw.text((x + radius + 2, y - radius - 2), str(guard["id"]), fill=color)
    for probe in annotations.get("edge_probes", []):
        draw.rectangle(tuple(probe["bbox"]), outline=(225, 180, 0), width=2)
        draw.text((probe["bbox"][0] + 2, probe["bbox"][1] + 2), str(probe["id"]), fill=(120, 85, 0))
    for review in annotations.get("human_review", []):
        if review.get("kind") == "bbox":
            draw.rectangle(tuple(review["bbox"]), outline=(230, 110, 0), width=2)
            draw.text(
                (review["bbox"][0] + 2, review["bbox"][1] + 2),
                str(review["id"]),
                fill=(150, 60, 0),
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    preview.save(path, optimize=True)


def case_by_id(manifest: Mapping[str, Any], case_id: str) -> Optional[Mapping[str, Any]]:
    for case in manifest.get("cases", []):
        if case.get("id") == case_id:
            return case
    return None


def verify_case(
    manifest: Mapping[str, Any],
    manifest_path: Path,
    case: Mapping[str, Any],
    candidate_path: Path,
    review_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    manifest_dir = manifest_path.parent
    product_root_raw = manifest.get("product_root")
    product_root = Path(str(product_root_raw)).expanduser().resolve() if product_root_raw else None
    contract = dict(manifest.get("contract", {}))
    failures: List[Dict[str, Any]] = []
    case_id = str(case.get("id", "<unknown>"))

    report: Dict[str, Any] = {
        "case_id": case_id,
        "candidate": str(candidate_path),
        "machine_pass": False,
        "final_verdict": "FAIL",
        "failures": failures,
    }
    if case.get("status") != "ready":
        failures.append(failure("benchmark_incomplete", f"case {case_id} is not ready"))
        return report

    original_spec = case.get("original")
    if not isinstance(original_spec, Mapping):
        failures.append(failure("case_spec_invalid", f"case {case_id} has no original asset"))
        return report
    original_path = validate_asset(original_spec, manifest_dir, product_root, f"{case_id} original", failures)

    reference_rows: List[Tuple[Mapping[str, Any], Optional[Path]]] = []
    for index, reference_spec in enumerate(case.get("references", [])):
        if not isinstance(reference_spec, Mapping):
            failures.append(failure("case_spec_invalid", f"{case_id} reference {index} is invalid"))
            continue
        reference_rows.append(
            (
                reference_spec,
                validate_asset(
                    reference_spec,
                    manifest_dir,
                    product_root,
                    f"{case_id} reference scale {reference_spec.get('scale')}",
                    failures,
                ),
            )
        )

    annotation_spec = case.get("annotations")
    annotations: Optional[Mapping[str, Any]] = None
    if isinstance(annotation_spec, Mapping):
        try:
            annotation_path = resolve_path(annotation_spec, manifest_dir, product_root)
            raw_annotations = load_json(annotation_path)
            if not isinstance(raw_annotations, Mapping):
                raise ValueError("annotation root must be an object")
            annotations = raw_annotations
            report["annotations"] = str(annotation_path)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            failures.append(failure("annotations_invalid", f"{case_id} annotations: {exc}"))
    else:
        failures.append(failure("annotations_missing", f"case {case_id} has no annotations"))

    if original_path is None or annotations is None or not reference_rows:
        return report

    try:
        paper_rgb, paper_rgb_source = resolve_paper_rgb(case, annotations, contract)
    except ValueError as exc:
        failures.append(failure("paper_contract_invalid", f"{case_id}: {exc}"))
        return report
    report["paper_rgb"] = paper_rgb
    report["paper_rgb_source"] = paper_rgb_source

    if not candidate_path.is_file():
        failures.append(failure("candidate_missing", f"candidate missing: {candidate_path}"))
        return report

    try:
        candidate = Image.open(candidate_path)
    except OSError as exc:
        failures.append(failure("candidate_unreadable", f"candidate unreadable: {exc}"))
        return report

    with candidate:
        report["candidate_sha256"] = sha256_file(candidate_path)
        report["candidate_format"] = candidate.format
        report["candidate_mode"] = candidate.mode
        report["candidate_dimensions"] = [candidate.width, candidate.height]
        if candidate.format != "PNG":
            failures.append(
                failure(
                    "candidate_format_invalid",
                    f"candidate must be PNG, got format={candidate.format}",
                    format=candidate.format,
                )
            )
            return report
        if candidate.mode != "RGBA":
            failures.append(
                failure(
                    "alpha_channel_missing",
                    f"candidate must be RGBA PNG, got mode={candidate.mode}",
                    mode=candidate.mode,
                )
            )
            return report

        matching: Optional[Tuple[Mapping[str, Any], Path]] = None
        for reference_spec, reference_path in reference_rows:
            if reference_path is None:
                continue
            if [candidate.width, candidate.height] == [
                int(reference_spec.get("width", -1)),
                int(reference_spec.get("height", -1)),
            ]:
                matching = (reference_spec, reference_path)
                break
        if matching is None:
            expected = [
                [int(spec.get("width", -1)), int(spec.get("height", -1))]
                for spec, _ in reference_rows
            ]
            failures.append(
                failure(
                    "candidate_dimension_mismatch",
                    "candidate dimensions do not match a frozen reference scale",
                    actual=[candidate.width, candidate.height],
                    expected=expected,
                )
            )
            return report

        reference_spec, reference_path = matching
        scale = float(reference_spec.get("scale", 0))
        expected_scale_x = candidate.width / float(original_spec["width"])
        expected_scale_y = candidate.height / float(original_spec["height"])
        if scale <= 0 or not math.isclose(expected_scale_x, scale) or not math.isclose(expected_scale_y, scale):
            failures.append(
                failure(
                    "reference_scale_mismatch",
                    "reference scale does not match original and candidate dimensions",
                    declared=scale,
                    measured=[expected_scale_x, expected_scale_y],
                )
            )
            return report
        report["reference"] = str(reference_path)
        report["scale"] = scale

        alpha = candidate.getchannel("A")
        alpha_hist = alpha.histogram()
        pixels = candidate.width * candidate.height
        alpha_background_max = int(contract.get("alpha_background_max", 16))
        alpha_foreground_min = int(contract.get("alpha_foreground_min", 96))
        background_fraction = float(sum(alpha_hist[: alpha_background_max + 1]) / pixels)
        foreground_fraction = float(sum(alpha_hist[alpha_foreground_min:]) / pixels)
        semitransparent_fraction = float(sum(alpha_hist[1:255]) / pixels)
        report["alpha"] = {
            "background_fraction": background_fraction,
            "foreground_fraction": foreground_fraction,
            "semitransparent_fraction": semitransparent_fraction,
            "unique_values": int(sum(1 for value in alpha_hist if value)),
        }
        if background_fraction < float(contract.get("min_background_fraction", 0.01)):
            failures.append(
                failure(
                    "alpha_background_missing",
                    "too little transparent background",
                    actual=background_fraction,
                    required=contract.get("min_background_fraction"),
                )
            )
        if foreground_fraction < float(contract.get("min_foreground_fraction", 0.01)):
            failures.append(
                failure(
                    "alpha_foreground_missing",
                    "too little retained foreground",
                    actual=foreground_fraction,
                    required=contract.get("min_foreground_fraction"),
                )
            )

        backgrounds = contract.get(
            "composite_backgrounds",
            {"white": [255, 255, 255], "gray": [140, 140, 140], "black": [0, 0, 0], "magenta": [255, 0, 255]},
        )
        with Image.open(reference_path) as reference:
            reconstruction, composite_metrics = scan_reconstruction_and_composites(
                candidate, reference, paper_rgb, backgrounds
            )
        report["straight_rgb_reconstruction"] = reconstruction
        report["composites"] = composite_metrics
        if reconstruction["mae"] > float(contract.get("reconstruction_mae_max", 1.5)) or reconstruction[
            "p99"
        ] > int(contract.get("reconstruction_p99_max", 8)):
            failures.append(
                failure(
                    "rgb_reconstruction",
                    "straight RGBA does not reconstruct the pre-removal RGB over paper",
                    metric=reconstruction,
                    mae_max=contract.get("reconstruction_mae_max"),
                    p99_max=contract.get("reconstruction_p99_max"),
                )
            )

        guard_failures, guard_metrics = check_guards(alpha, annotations, scale)
        failures.extend(guard_failures)
        report["guard_metrics"] = guard_metrics

        edge_failures, edge_metrics = check_edges(
            candidate, annotations, scale, paper_rgb, alpha_background_max
        )
        failures.extend(edge_failures)
        report["edge_metrics"] = edge_metrics

        review_rows = [row for row in annotations.get("human_review", []) if row.get("required", True)]
        report["human_review_required"] = bool(review_rows)
        report["human_review"] = review_rows
        if review_dir is not None:
            report["review_artifacts"] = write_review_artifacts(
                original_path, candidate, annotations, scale, backgrounds, review_dir, case_id
            )

    report["machine_pass"] = not failures
    if failures:
        report["final_verdict"] = "FAIL"
    elif report.get("human_review_required"):
        report["final_verdict"] = "PENDING_HUMAN_REVIEW"
    else:
        report["final_verdict"] = "PASS"
    return report


def parse_candidate_overrides(values: Iterable[str]) -> Dict[str, Path]:
    parsed: Dict[str, Path] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(f"candidate override must be CASE=PATH: {raw!r}")
        case_id, path = raw.split("=", 1)
        case_id = case_id.strip()
        if not case_id or not path.strip():
            raise ValueError(f"candidate override must be CASE=PATH: {raw!r}")
        parsed[case_id] = Path(path.strip()).expanduser().resolve()
    return parsed


def verify_manifest(
    manifest_path: Path,
    candidate_overrides: Mapping[str, Path],
    selected_cases: Optional[Sequence[str]] = None,
    review_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    manifest = load_json(manifest_path)
    if not isinstance(manifest, Mapping):
        raise ValueError("manifest root must be an object")
    selected = list(selected_cases) if selected_cases else list(candidate_overrides)
    if not selected:
        selected = [str(case.get("id")) for case in manifest.get("cases", []) if case.get("candidate")]
    reports: List[Dict[str, Any]] = []
    for case_id in selected:
        case = case_by_id(manifest, case_id)
        if case is None:
            reports.append(
                {
                    "case_id": case_id,
                    "machine_pass": False,
                    "final_verdict": "FAIL",
                    "failures": [failure("case_missing", f"case not found: {case_id}")],
                }
            )
            continue
        candidate_path = candidate_overrides.get(case_id)
        if candidate_path is None and isinstance(case.get("candidate"), Mapping):
            product_root_raw = manifest.get("product_root")
            product_root = Path(str(product_root_raw)).expanduser().resolve() if product_root_raw else None
            candidate_path = resolve_path(case["candidate"], manifest_path.parent, product_root)
        if candidate_path is None:
            reports.append(
                {
                    "case_id": case_id,
                    "machine_pass": False,
                    "final_verdict": "FAIL",
                    "failures": [failure("candidate_missing", f"no candidate supplied for {case_id}")],
                }
            )
            continue
        case_review_dir = review_dir / safe_slug(case_id) if review_dir else None
        reports.append(verify_case(manifest, manifest_path, case, candidate_path, case_review_dir))
    return {
        "schema_version": 1,
        "manifest": str(manifest_path),
        "machine_pass": bool(reports) and all(report.get("machine_pass") for report in reports),
        "reports": reports,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument(
        "--candidate",
        action="append",
        default=[],
        metavar="CASE=PATH",
        help="Candidate override; repeat for multiple cases.",
    )
    parser.add_argument("--case", action="append", default=None, help="Case id to verify; repeatable.")
    parser.add_argument("--json-report", type=Path)
    parser.add_argument("--review-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.expanduser().resolve()
    try:
        overrides = parse_candidate_overrides(args.candidate)
        report = verify_manifest(
            manifest_path,
            overrides,
            selected_cases=args.case,
            review_dir=args.review_dir.expanduser().resolve() if args.review_dir else None,
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.json_report:
        output_path = args.json_report.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for case_report in report["reports"]:
        print(
            f"{case_report['case_id']}: {case_report['final_verdict']} "
            f"machine_pass={str(case_report.get('machine_pass', False)).lower()}"
        )
        for item in case_report.get("failures", []):
            print(f"  FAIL {item['code']}: {item['message']}")
        if case_report.get("human_review_required") and case_report.get("machine_pass"):
            print("  Human review remains required on native white/gray/black/magenta crops.")
    print(f"OVERALL machine_pass={str(report['machine_pass']).lower()}")
    return 0 if report["machine_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
