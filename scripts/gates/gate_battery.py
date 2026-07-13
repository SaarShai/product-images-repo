#!/usr/bin/env python3
"""Transparent-background defect detector battery.

One CLI entry point:
  python3 scripts/gates/gate_battery.py --rgba IMG.png --out-dir OUT

The battery writes OUT/battery.json and per-gate 1:1 evidence crops for failed
gates. Optional inputs enable source-aware deleted-art detection (D5) and
key-color spill detection (D6).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import rgb2lab


REPO = Path(__file__).resolve().parents[2]


# Calibration provenance:
# - Initial hard gates follow tasks/transparent-bg-endgame/DETECTORS-SPEC.md.
# - D4 uses scripts/aura_gate.py's already calibrated FAIL_THRESH=0.20.
# - D7 is deterministic project policy: any nonzero 3px border alpha fails.
# - D8 flat-alpha/checkerboard thresholds are synthetic-regression thresholds.
# - D1/D2/D3/D5/D6 were tuned against the local known-good/known-bad sweep
#   recorded in tasks/transparent-bg-endgame/CALIBRATION.md; detectors with
#   limited real-data separation are marked advisory in output.
CALIBRATION: dict[str, dict[str, Any]] = {
    "D1_halo_gate": {
        "edge_l99_max": 16.0,
        "edge_l_mean_max": 3.5,
        "bright_run_l_min": 20.0,
        "advisory": False,
    },
    "D2_soft_alpha_fringe": {
        "soft_perimeter_ratio_max_soft": 2.75,
        "soft_perimeter_ratio_max_print": 0.0,
        "transition_width_p95_max": 4.0,
        "advisory": False,
    },
    "D3_pocket_gate": {
        "max_count": 4,
        "max_total_area_frac": 1.0,
        "max_component_area_frac": 1.0,
        "min_component_area": 4,
        "advisory": False,
    },
    "D4_aura_gate": {
        "aura_index_max": 0.20,
        "advisory": False,
    },
    "D5_hole_gate": {
        "expected_fg_delta_e_min": 8.0,
        "deleted_area_frac_max": 0.002,
        "deleted_component_area_max": 64,
        "advisory": True,
    },
    "D6_spill_gate": {
        "oklab_delta_chroma_max": 0.055,
        "bg_projection_max": 0.040,
        "advisory": True,
    },
    "D7_border_gate": {
        "border_alpha_occupancy_max": 0.0,
        "strip_px": 3,
        "advisory": False,
    },
    "D8_alpha_sanity": {
        "checker_ratio_max": 0.25,
        "checker_delta_min": 20.0,
        "advisory": False,
    },
}


def load_rgba(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA"))


def parse_hex_color(value: str | None) -> tuple[int, int, int] | None:
    if value is None:
        return None
    raw = value.strip().lstrip("#")
    if len(raw) != 6:
        raise argparse.ArgumentTypeError(f"expected #RRGGBB, got {value!r}")
    try:
        return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected #RRGGBB, got {value!r}") from exc


def composite_rgb(rgba: np.ndarray, bg: tuple[int, int, int]) -> np.ndarray:
    rgb = rgba[..., :3].astype(np.float32)
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    bg_arr = np.array(bg, dtype=np.float32)
    return np.clip(np.round(rgb * alpha + bg_arr * (1.0 - alpha)), 0, 255).astype(np.uint8)


def rgb_to_lab_l(rgb: np.ndarray) -> np.ndarray:
    lab = rgb2lab(rgb.astype(np.float32) / 255.0)
    return lab[..., 0]


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    rgb = np.clip(rgb.astype(np.float32) / 255.0, 0.0, 1.0)
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def rgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    linear = srgb_to_linear(rgb)
    l = 0.4122214708 * linear[..., 0] + 0.5363325363 * linear[..., 1] + 0.0514459929 * linear[..., 2]
    m = 0.2119034982 * linear[..., 0] + 0.6806995451 * linear[..., 1] + 0.1073969566 * linear[..., 2]
    s = 0.0883024619 * linear[..., 0] + 0.2817188376 * linear[..., 1] + 0.6299787005 * linear[..., 2]
    lms = np.cbrt(np.stack([l, m, s], axis=-1))
    return np.stack(
        [
            0.2104542553 * lms[..., 0] + 0.7936177850 * lms[..., 1] - 0.0040720468 * lms[..., 2],
            1.9779984951 * lms[..., 0] - 2.4285922050 * lms[..., 1] + 0.4505937099 * lms[..., 2],
            0.0259040371 * lms[..., 0] + 0.7827717662 * lms[..., 1] - 0.8086757660 * lms[..., 2],
        ],
        axis=-1,
    )


def disk(radius: int) -> np.ndarray:
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (xx * xx + yy * yy) <= radius * radius


def empty_gate(name: str, skipped_reason: str | None = None) -> dict[str, Any]:
    gate = {
        "metric_values": {},
        "threshold": CALIBRATION[name].copy(),
        "pass": True,
        "advisory": bool(CALIBRATION[name].get("advisory", False)),
        "crop_paths": [],
    }
    if skipped_reason:
        gate["skipped"] = True
        gate["skip_reason"] = skipped_reason
    return gate


def crop_box(mask: np.ndarray, pad: int = 24, bounds: tuple[int, int] | None = None) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    h, w = mask.shape if bounds is None else bounds
    x0 = max(0, int(xs.min()) - pad)
    y0 = max(0, int(ys.min()) - pad)
    x1 = min(w, int(xs.max()) + pad + 1)
    y1 = min(h, int(ys.max()) + pad + 1)
    return (x0, y0, x1, y1)


def save_crop(image: np.ndarray, mask: np.ndarray, out_dir: Path, gate: str, label: str, pad: int = 24) -> str | None:
    box = crop_box(mask, pad=pad)
    if box is None:
        return None
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{gate}-{label}.png"
    Image.fromarray(image).crop(box).save(path)
    return str(path)


def component_crops(
    image: np.ndarray,
    labels: np.ndarray,
    components: list[tuple[int, int]],
    out_dir: Path,
    gate: str,
    limit: int = 5,
) -> list[str]:
    paths: list[str] = []
    for rank, (lbl, _area) in enumerate(components[:limit], start=1):
        path = save_crop(image, labels == lbl, out_dir, gate, f"component-{rank}", pad=24)
        if path:
            paths.append(path)
    return paths


def max_run(mask: np.ndarray) -> int:
    best = 0
    for axis in (0, 1):
        arr = mask if axis == 0 else mask.T
        for row in arr:
            if not row.any():
                continue
            padded = np.pad(row.astype(np.int8), (1, 1), constant_values=0)
            changes = np.diff(padded)
            starts = np.nonzero(changes == 1)[0]
            ends = np.nonzero(changes == -1)[0]
            if len(starts):
                best = max(best, int((ends - starts).max()))
    return best


def d1_halo_gate(rgba: np.ndarray, out_dir: Path) -> dict[str, Any]:
    cfg = CALIBRATION["D1_halo_gate"]
    alpha = rgba[..., 3]
    fg = alpha > 127
    edge_band = ndi.binary_dilation(fg, structure=disk(3)) & ~fg
    inner_ref = fg & ~ndi.binary_erosion(fg, structure=disk(5))
    comp_black = composite_rgb(rgba, (0, 0, 0))
    lstar = rgb_to_lab_l(comp_black)
    edge_vals = lstar[edge_band]
    inner_vals = lstar[inner_ref]
    if edge_vals.size == 0:
        metric = {"edge_band_px": 0, "edge_l_mean": 0.0, "edge_l_p99": 0.0, "inner_l_mean": 0.0, "bright_run_max": 0}
        passed = True
        offender = np.zeros(alpha.shape, dtype=bool)
    else:
        bright = edge_band & (lstar > float(cfg["bright_run_l_min"]))
        metric = {
            "edge_band_px": int(edge_band.sum()),
            "edge_l_mean": round(float(edge_vals.mean()), 4),
            "edge_l_p99": round(float(np.percentile(edge_vals, 99)), 4),
            "inner_l_mean": round(float(inner_vals.mean()), 4) if inner_vals.size else 0.0,
            "bright_run_max": max_run(bright),
        }
        passed = metric["edge_l_p99"] <= cfg["edge_l99_max"] and metric["edge_l_mean"] <= cfg["edge_l_mean_max"]
        offender = edge_band & (lstar > cfg["edge_l99_max"])
    crop_paths = []
    if not passed:
        crop = save_crop(rgba, offender if offender.any() else edge_band, out_dir, "D1_halo_gate", "edge-band")
        if crop:
            crop_paths.append(crop)
    return {
        "metric_values": metric,
        "threshold": cfg.copy(),
        "pass": bool(passed),
        "advisory": bool(cfg.get("advisory", False)),
        "crop_paths": crop_paths,
    }


def d2_soft_alpha_fringe(rgba: np.ndarray, out_dir: Path, profile: str) -> dict[str, Any]:
    cfg = CALIBRATION["D2_soft_alpha_fringe"]
    alpha = rgba[..., 3]
    fg_any = alpha > 0
    fg_opaque = alpha > 127
    boundary = fg_opaque & ~ndi.binary_erosion(fg_opaque, structure=np.ones((3, 3), dtype=bool))
    soft = (alpha > 0) & (alpha < 255)
    soft_count = int(soft.sum())
    perimeter = int(boundary.sum())
    soft_ratio = float(soft_count / max(perimeter, 1))
    if soft.any():
        soft_width = ndi.distance_transform_edt(soft)
        p95 = float(np.percentile(soft_width[soft], 95))
        max_width = float(soft_width[soft].max())
    else:
        p95 = 0.0
        max_width = 0.0
    ratio_thresh = cfg["soft_perimeter_ratio_max_print"] if profile == "print" else cfg["soft_perimeter_ratio_max_soft"]
    passed = soft_ratio <= ratio_thresh and p95 <= cfg["transition_width_p95_max"]
    if profile == "print":
        passed = passed and soft_count == 0
    metric = {
        "soft_px": soft_count,
        "fg_nonzero_px": int(fg_any.sum()),
        "boundary_perimeter_px": perimeter,
        "soft_perimeter_ratio": round(soft_ratio, 4),
        "transition_width_p95": round(p95, 4),
        "transition_width_max": round(max_width, 4),
        "profile": profile,
    }
    crop_paths = []
    if not passed:
        crop = save_crop(rgba, soft, out_dir, "D2_soft_alpha_fringe", "soft-alpha")
        if crop:
            crop_paths.append(crop)
    threshold = cfg.copy()
    threshold["active_soft_perimeter_ratio_max"] = ratio_thresh
    return {
        "metric_values": metric,
        "threshold": threshold,
        "pass": bool(passed),
        "advisory": bool(cfg.get("advisory", False)),
        "crop_paths": crop_paths,
    }


def border_connected(mask: np.ndarray) -> np.ndarray:
    labels, n = ndi.label(mask, structure=np.ones((3, 3), dtype=bool))
    if n == 0:
        return np.zeros_like(mask, dtype=bool)
    border_labels = np.unique(np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]))
    border_labels = border_labels[border_labels != 0]
    return np.isin(labels, border_labels)


def d3_pocket_gate(rgba: np.ndarray, out_dir: Path) -> dict[str, Any]:
    cfg = CALIBRATION["D3_pocket_gate"]
    alpha = rgba[..., 3]
    transparent = alpha == 0
    pockets = transparent & ~border_connected(transparent)
    labels, n = ndi.label(pockets, structure=np.ones((3, 3), dtype=bool))
    areas = [(lbl, int((labels == lbl).sum())) for lbl in range(1, n + 1)]
    areas = [(lbl, area) for lbl, area in areas if area >= cfg["min_component_area"]]
    areas.sort(key=lambda item: item[1], reverse=True)
    total_area = int(sum(area for _lbl, area in areas))
    image_area = int(alpha.size)
    max_area = areas[0][1] if areas else 0
    passed = (
        len(areas) <= cfg["max_count"]
        and total_area / max(image_area, 1) <= cfg["max_total_area_frac"]
        and max_area / max(image_area, 1) <= cfg["max_component_area_frac"]
    )
    metric = {
        "component_count": len(areas),
        "total_area_px": total_area,
        "max_area_px": max_area,
        "total_area_frac": round(float(total_area / max(image_area, 1)), 6),
        "max_area_frac": round(float(max_area / max(image_area, 1)), 6),
    }
    crop_paths = component_crops(rgba, labels, areas, out_dir, "D3_pocket_gate") if not passed else []
    return {
        "metric_values": metric,
        "threshold": cfg.copy(),
        "pass": bool(passed),
        "advisory": bool(cfg.get("advisory", False)),
        "crop_paths": crop_paths,
    }


def load_aura_module():
    aura_path = REPO / "scripts" / "aura_gate.py"
    spec = importlib.util.spec_from_file_location("_gate_battery_aura_gate", aura_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {aura_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def d4_aura_gate(rgba_path: Path, out_dir: Path) -> dict[str, Any]:
    cfg = CALIBRATION["D4_aura_gate"]
    overlay_path = out_dir / "D4_aura_gate-overlay.png"
    try:
        aura_gate = load_aura_module()
        result = aura_gate.score_image(rgba_path, overlay_path=overlay_path, fail_thresh=cfg["aura_index_max"])
        passed = result.get("verdict") == "PASS"
        crop_paths = [str(overlay_path)] if overlay_path.exists() and not passed else []
        return {
            "metric_values": result,
            "threshold": cfg.copy(),
            "pass": bool(passed),
            "advisory": bool(cfg.get("advisory", False)),
            "crop_paths": crop_paths,
        }
    except Exception as exc:  # pragma: no cover - defensive: reports rather than hiding D4 failure.
        return {
            "metric_values": {"error": str(exc)},
            "threshold": cfg.copy(),
            "pass": False,
            "advisory": bool(cfg.get("advisory", False)),
            "crop_paths": [],
        }


def d5_hole_gate(rgba: np.ndarray, source_path: Path | None, bg: tuple[int, int, int] | None, out_dir: Path) -> dict[str, Any]:
    cfg = CALIBRATION["D5_hole_gate"]
    if source_path is None:
        return empty_gate("D5_hole_gate", "--source not provided")
    src = np.asarray(Image.open(source_path).convert("RGB"))
    if src.shape[:2] != rgba.shape[:2]:
        raise ValueError(f"--source size {src.shape[:2]} does not match --rgba size {rgba.shape[:2]}")
    bg_rgb = np.array(bg if bg is not None else (255, 255, 255), dtype=np.float32)
    lab = rgb2lab(src.astype(np.float32) / 255.0)
    bg_lab = rgb2lab((bg_rgb.reshape(1, 1, 3) / 255.0)).reshape(3)
    delta_e = np.linalg.norm(lab - bg_lab[None, None, :], axis=2)
    expected_fg = delta_e >= cfg["expected_fg_delta_e_min"]
    delivered = rgba[..., 3] > 0
    deleted = expected_fg & ~delivered
    labels, n = ndi.label(deleted, structure=np.ones((3, 3), dtype=bool))
    areas = [(lbl, int((labels == lbl).sum())) for lbl in range(1, n + 1)]
    areas.sort(key=lambda item: item[1], reverse=True)
    dist = ndi.distance_transform_edt(deleted)
    strata = {"thin": {"count": 0, "area_px": 0}, "medium": {"count": 0, "area_px": 0}, "thick": {"count": 0, "area_px": 0}}
    comp_metrics = []
    for lbl, area in areas:
        comp = labels == lbl
        thinness = float(dist[comp].max()) if comp.any() else 0.0
        bucket = "thin" if thinness <= 2.0 else "medium" if thinness <= 5.0 else "thick"
        strata[bucket]["count"] += 1
        strata[bucket]["area_px"] += area
        comp_metrics.append({"label": lbl, "area_px": area, "distance_transform_max": round(thinness, 3), "bucket": bucket})
    expected_area = int(expected_fg.sum())
    deleted_area = int(deleted.sum())
    deleted_frac = float(deleted_area / max(expected_area, 1))
    max_area = areas[0][1] if areas else 0
    passed = deleted_frac <= cfg["deleted_area_frac_max"] and max_area <= cfg["deleted_component_area_max"]
    metric = {
        "background_rgb": [int(x) for x in bg_rgb],
        "expected_fg_px": expected_area,
        "deleted_art_px": deleted_area,
        "deleted_area_frac_of_expected": round(deleted_frac, 6),
        "deleted_component_count": len(areas),
        "deleted_component_max_area_px": max_area,
        "strata": strata,
        "worst_components": comp_metrics[:5],
    }
    crop_paths = component_crops(rgba, labels, areas, out_dir, "D5_hole_gate") if not passed else []
    return {
        "metric_values": metric,
        "threshold": cfg.copy(),
        "pass": bool(passed),
        "advisory": bool(cfg.get("advisory", False)),
        "crop_paths": crop_paths,
    }


def d6_spill_gate(rgba: np.ndarray, bg: tuple[int, int, int] | None, out_dir: Path) -> dict[str, Any]:
    cfg = CALIBRATION["D6_spill_gate"]
    if bg is None:
        return empty_gate("D6_spill_gate", "--bg-color not provided")
    alpha = rgba[..., 3]
    fg = alpha > 0
    opaque = alpha >= 250
    if fg.sum() < 25 or opaque.sum() < 25:
        return empty_gate("D6_spill_gate", "insufficient foreground/interior pixels")
    dist = ndi.distance_transform_edt(fg)
    edge = fg & (dist <= 4)
    interior = ndi.binary_erosion(opaque, structure=disk(8)) & opaque
    if interior.sum() < 25:
        interior = opaque & (dist > 6)
    if edge.sum() < 25 or interior.sum() < 25:
        return empty_gate("D6_spill_gate", "insufficient edge/interior pixels")
    oklab = rgb_to_oklab(rgba[..., :3])
    edge_ab = oklab[..., 1:3][edge]
    interior_ab = oklab[..., 1:3][interior]
    edge_mean = edge_ab.mean(axis=0)
    interior_mean = interior_ab.mean(axis=0)
    delta_vec = edge_mean - interior_mean
    delta = float(np.linalg.norm(delta_vec))
    bg_lab = rgb_to_oklab(np.array(bg, dtype=np.uint8).reshape(1, 1, 3))[0, 0, 1:3]
    bg_norm = float(np.linalg.norm(bg_lab))
    projection = 0.0 if bg_norm == 0.0 else float(np.dot(delta_vec, bg_lab / bg_norm))
    passed = delta <= cfg["oklab_delta_chroma_max"] and projection <= cfg["bg_projection_max"]
    metric = {
        "background_rgb": list(bg),
        "edge_px": int(edge.sum()),
        "interior_px": int(interior.sum()),
        "edge_oklab_ab_mean": [round(float(x), 6) for x in edge_mean],
        "interior_oklab_ab_mean": [round(float(x), 6) for x in interior_mean],
        "oklab_delta_chroma": round(delta, 6),
        "bg_chroma_projection": round(projection, 6),
    }
    crop_paths = []
    if not passed:
        crop = save_crop(rgba, edge, out_dir, "D6_spill_gate", "edge-band")
        if crop:
            crop_paths.append(crop)
    return {
        "metric_values": metric,
        "threshold": cfg.copy(),
        "pass": bool(passed),
        "advisory": bool(cfg.get("advisory", False)),
        "crop_paths": crop_paths,
    }


def d7_border_gate(rgba: np.ndarray, out_dir: Path) -> dict[str, Any]:
    cfg = CALIBRATION["D7_border_gate"]
    alpha = rgba[..., 3]
    strip = int(cfg["strip_px"])
    border = np.zeros(alpha.shape, dtype=bool)
    border[:strip, :] = True
    border[-strip:, :] = True
    border[:, :strip] = True
    border[:, -strip:] = True
    occupied = border & (alpha > 0)
    occupancy = float(occupied.sum() / max(border.sum(), 1))
    passed = occupancy <= cfg["border_alpha_occupancy_max"]
    metric = {
        "strip_px": strip,
        "border_px": int(border.sum()),
        "occupied_px": int(occupied.sum()),
        "border_alpha_occupancy": round(occupancy, 8),
    }
    crop_paths = []
    if not passed:
        crop = save_crop(rgba, occupied, out_dir, "D7_border_gate", "occupied-border", pad=8)
        if crop:
            crop_paths.append(crop)
    return {
        "metric_values": metric,
        "threshold": cfg.copy(),
        "pass": bool(passed),
        "advisory": bool(cfg.get("advisory", False)),
        "crop_paths": crop_paths,
    }


def checkerboard_ratio(rgb: np.ndarray, opaque: np.ndarray, delta_min: float) -> tuple[float, int]:
    luma = 0.299 * rgb[..., 0].astype(np.float32) + 0.587 * rgb[..., 1].astype(np.float32) + 0.114 * rgb[..., 2].astype(np.float32)
    h, w = opaque.shape
    if h < 2 or w < 2:
        return 0.0, 0
    m = opaque[:-1, :-1] & opaque[1:, :-1] & opaque[:-1, 1:] & opaque[1:, 1:]
    total = int(m.sum())
    if total == 0:
        return 0.0, 0
    a = luma[:-1, :-1]
    b = luma[:-1, 1:]
    c = luma[1:, :-1]
    d = luma[1:, 1:]
    pattern = m & (np.abs(a - d) <= 6) & (np.abs(b - c) <= 6) & (np.abs(a - b) >= delta_min)
    return float(pattern.sum() / total), total


def d8_alpha_sanity(rgba: np.ndarray, out_dir: Path) -> dict[str, Any]:
    cfg = CALIBRATION["D8_alpha_sanity"]
    alpha = rgba[..., 3]
    unique = np.unique(alpha)
    total = alpha.size
    zero = int((alpha == 0).sum())
    soft = int(((alpha > 0) & (alpha < 255)).sum())
    opaque = int((alpha == 255).sum())
    checker_ratio, checker_blocks = checkerboard_ratio(rgba[..., :3], alpha == 255, cfg["checker_delta_min"])
    flat_alpha = len(unique) == 1
    lacks_transparency = zero == 0
    lacks_foreground = (alpha > 0).sum() == 0
    checker_fail = checker_ratio > cfg["checker_ratio_max"]
    passed = not (flat_alpha or lacks_transparency or lacks_foreground or checker_fail)
    metric = {
        "alpha_min": int(alpha.min()),
        "alpha_max": int(alpha.max()),
        "alpha_unique_count": int(len(unique)),
        "alpha_unique_sample": [int(x) for x in unique[:16]],
        "zero_px": zero,
        "soft_px": soft,
        "opaque_px": opaque,
        "zero_frac": round(float(zero / total), 6),
        "soft_frac": round(float(soft / total), 6),
        "opaque_frac": round(float(opaque / total), 6),
        "flat_alpha": bool(flat_alpha),
        "lacks_transparency": bool(lacks_transparency),
        "lacks_foreground": bool(lacks_foreground),
        "checker_ratio": round(checker_ratio, 6),
        "checker_2x2_blocks": checker_blocks,
        "checker_fail": bool(checker_fail),
    }
    crop_paths = []
    if checker_fail:
        crop = save_crop(rgba, alpha == 255, out_dir, "D8_alpha_sanity", "checker-opaque", pad=24)
        if crop:
            crop_paths.append(crop)
    elif not passed:
        mask = alpha > 0 if (alpha > 0).any() else np.ones(alpha.shape, dtype=bool)
        crop = save_crop(rgba, mask, out_dir, "D8_alpha_sanity", "alpha-degenerate", pad=24)
        if crop:
            crop_paths.append(crop)
    return {
        "metric_values": metric,
        "threshold": cfg.copy(),
        "pass": bool(passed),
        "advisory": bool(cfg.get("advisory", False)),
        "crop_paths": crop_paths,
    }


def run_battery(
    rgba_path: Path,
    source_path: Path | None,
    bg_color: tuple[int, int, int] | None,
    profile: str,
    out_dir: Path,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rgba = load_rgba(rgba_path)
    gates = {
        "D1_halo_gate": d1_halo_gate(rgba, out_dir),
        "D2_soft_alpha_fringe": d2_soft_alpha_fringe(rgba, out_dir, profile),
        "D3_pocket_gate": d3_pocket_gate(rgba, out_dir),
        "D4_aura_gate": d4_aura_gate(rgba_path, out_dir),
        "D5_hole_gate": d5_hole_gate(rgba, source_path, bg_color, out_dir),
        "D6_spill_gate": d6_spill_gate(rgba, bg_color, out_dir),
        "D7_border_gate": d7_border_gate(rgba, out_dir),
        "D8_alpha_sanity": d8_alpha_sanity(rgba, out_dir),
    }
    all_pass = all(gate["pass"] for gate in gates.values())
    battery = {
        "rgba": str(rgba_path),
        "source": str(source_path) if source_path else None,
        "bg_color": f"#{bg_color[0]:02X}{bg_color[1]:02X}{bg_color[2]:02X}" if bg_color else None,
        "profile": profile,
        "pass": bool(all_pass),
        "gates": gates,
    }
    (out_dir / "battery.json").write_text(json.dumps(battery, indent=2))
    return battery


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rgba", required=True, type=Path)
    ap.add_argument("--source", type=Path, default=None)
    ap.add_argument("--bg-color", type=parse_hex_color, default=None)
    ap.add_argument("--profile", choices=("print", "soft"), default="soft")
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args(argv)

    battery = run_battery(args.rgba, args.source, args.bg_color, args.profile, args.out_dir)
    print(json.dumps({"pass": battery["pass"], "battery_json": str(args.out_dir / "battery.json")}, indent=2))
    return 0 if battery["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
