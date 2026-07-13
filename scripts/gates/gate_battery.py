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
from skimage.color import deltaE_ciede2000, rgb2lab
from skimage.measure import perimeter as measure_perimeter
from skimage.morphology import skeletonize


REPO = Path(__file__).resolve().parents[2]


# Calibration provenance:
# - v1 hard gates follow tasks/transparent-bg-endgame/DETECTORS-SPEC.md.
# - v2 formulas follow advisor-sol-ultra.md section 4; thresholds below are
#   screening seeds, not print-calibrated production standards.
# - D4 uses scripts/aura_gate.py's already calibrated FAIL_THRESH=0.20.
# - D7 default auto policy downgrades edge-touching art to REVIEW; forbid
#   preserves the isolated-subject hard-fail behavior.
# - D8 flat-alpha/checkerboard thresholds are synthetic-regression thresholds.
# - D1/D2/D3/D5/D6 were tuned against the local known-good/known-bad sweep
#   recorded in tasks/transparent-bg-endgame/CALIBRATION.md; detectors with
#   limited real-data separation are marked advisory in output.
CALIBRATION: dict[str, dict[str, Any]] = {
    "D1_halo_gate": {
        "band_mm": 0.30,
        "donor_min_mm": 0.15,
        "donor_max_mm": 0.35,
        "h_l_pass_max": 2.0,
        "h_l_fail_min": 6.0,
        "h_area_pass_max_mm2": 0.02,
        "h_area_fail_min_mm2": 0.10,
        "h_key_pass_max": 0.15,
        "h_key_fail_min": 0.35,
        "px_edge_l99_fail_min": 16.0,
        "px_edge_l_mean_fail_min": 3.5,
        "advisory": False,
    },
    "D2_soft_alpha_fringe": {
        "w10_90_p95_pass_max_mm": 0.20,
        "w10_90_p95_fail_min_mm": 0.40,
        "contour_disp_p95_pass_max_mm": 0.08,
        "contour_disp_p95_fail_min_mm": 0.18,
        "perimeter_excess_pass_max": 0.20,
        "perimeter_excess_fail_min": 0.60,
        "smooth_mm": 0.15,
        "soft_perimeter_ratio_max_soft": 2.75,
        "soft_perimeter_ratio_max_print": 0.0,
        "transition_width_p95_max": 4.0,
        "advisory": False,
    },
    "D3a_alpha_pockets": {
        "review_count_per_mpx_min": 1000.0,
        "max_total_area_frac": 1.0,
        "max_component_area_frac": 1.0,
        "min_component_area_px": 9,
        "min_component_area_mm2": 0.02,
        "advisory": True,
    },
    "D3b_retained_background": {
        "tau_b_delta_e00": 6.0,
        "max_count": 0,
        "max_total_area_frac": 0.0,
        "max_component_area_frac": 0.0,
        "advisory": False,
    },
    "D4_aura_gate": {
        "aura_index_max": 0.20,
        "shell_min_mm": 0.10,
        "shell_max_mm": 1.00,
        "shell_l_min": 85.0,
        "shell_chroma_max": 8.0,
        "shell_texture_std_max": 2.0,
        "wrap_fraction_review_min": 0.15,
        "wrap_fraction_fail_min": 0.30,
        "median_width_review_min_mm": 0.10,
        "median_width_fail_min_mm": 0.20,
        "advisory": False,
    },
    "D5_hole_gate": {
        "truth_recall_pass_min": 0.98,
        "truth_recall_fail_below": 0.90,
        "truth_component_survival_pass_min": 1.0,
        "truth_component_survival_fail_below": 0.98,
        "truth_skeleton_breaks_pass_max": 0,
        "thin_bin_max_mm": 0.20,
        "medium_bin_max_mm": 0.50,
        "expected_fg_delta_e_min": 8.0,
        "deleted_area_frac_max": 0.002,
        "deleted_component_area_max": 64,
        "advisory": True,
    },
    "D6_spill_gate": {
        "band_mm": 0.30,
        "tau_clean": 0.01,
        "spill_p95_pass_max": 0.01,
        "spill_review_min": 0.01,
        "spill_area_review_min_mm2": 0.02,
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


DEFAULT_PANELS: tuple[tuple[int, int, int], ...] = (
    (0, 0, 0),
    (17, 17, 17),
    (0, 17, 58),
    (255, 0, 255),
)

PRESCRIBED_ACTIONS = {
    "D1_halo_gate": "halo -> decontaminate from stored soft alpha",
    "D2_soft_alpha_fringe": "edge damage -> recover from stored soft alpha or alternate extraction",
    "D3a_alpha_pockets": "alpha pockets -> human topology review only",
    "D3b_retained_background": "retained background -> global-key candidate",
    "D4_aura_gate": "aura -> regenerate",
    "D5_hole_gate": "hole -> reject/alternate extraction",
    "D6_spill_gate": "spill -> bounded despill",
    "D7_border_gate": "border -> reframe or regenerate with clear margin",
    "D8_alpha_sanity": "alpha sanity -> reject/alternate extraction",
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


def parse_panel_list(value: str | None) -> list[tuple[int, int, int]]:
    if not value:
        return []
    return [parse_hex_color(item) for item in value.split(",") if item.strip()]  # type: ignore[list-item]


def mm_per_px_from_args(ppi: float | None, px_per_mm: float | None) -> tuple[float | None, dict[str, Any]]:
    if ppi is not None and px_per_mm is not None:
        raise ValueError("provide only one of --ppi or --px-per-mm")
    if ppi is not None:
        if ppi <= 0:
            raise ValueError("--ppi must be > 0")
        return 25.4 / float(ppi), {"physical_units": True, "ppi": float(ppi), "px_per_mm": float(ppi) / 25.4}
    if px_per_mm is not None:
        if px_per_mm <= 0:
            raise ValueError("--px-per-mm must be > 0")
        return 1.0 / float(px_per_mm), {"physical_units": True, "ppi": float(px_per_mm) * 25.4, "px_per_mm": float(px_per_mm)}
    return None, {
        "physical_units": False,
        "units_advisory": "ppi/px-per-mm missing; mm thresholds reported as REVIEW-only fallbacks where needed",
    }


def mm_to_px(mm: float, mm_per_px: float | None, fallback_px: float) -> float:
    if mm_per_px is None:
        return float(fallback_px)
    return float(mm) / mm_per_px


def px_area_to_mm2(px: int | float, mm_per_px: float | None) -> float | None:
    if mm_per_px is None:
        return None
    return float(px) * mm_per_px * mm_per_px


def verdict_gate(
    name: str,
    verdict: str,
    metric: dict[str, Any],
    crop_paths: list[str] | None = None,
    threshold: dict[str, Any] | None = None,
    skipped_reason: str | None = None,
) -> dict[str, Any]:
    if verdict not in {"PASS", "FAIL", "REVIEW"}:
        raise ValueError(f"invalid gate verdict {verdict!r}")
    gate = {
        "metric_values": metric,
        "threshold": threshold if threshold is not None else CALIBRATION[name].copy(),
        "verdict": verdict,
        "pass": verdict == "PASS",
        "advisory": bool(CALIBRATION[name].get("advisory", False)),
        "crop_paths": crop_paths or [],
    }
    if skipped_reason:
        gate["skipped"] = True
        gate["skip_reason"] = skipped_reason
    return gate


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


def linear_to_srgb(rgb: np.ndarray) -> np.ndarray:
    rgb = np.clip(rgb.astype(np.float32), 0.0, 1.0)
    return np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * (rgb ** (1 / 2.4)) - 0.055)


def lab_l_from_linear(rgb_linear: np.ndarray) -> np.ndarray:
    return rgb_to_lab_l(np.clip(np.round(linear_to_srgb(rgb_linear) * 255.0), 0, 255).astype(np.uint8))


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
    return verdict_gate(name, "PASS", {}, skipped_reason=skipped_reason)


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


def support_signed_distance(alpha: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    support = alpha >= 0.5
    inside = ndi.distance_transform_edt(support)
    outside = ndi.distance_transform_edt(~support)
    return inside - outside, support


def weighted_percentile(values: np.ndarray, weights: np.ndarray, percentile: float) -> float:
    values = np.asarray(values, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not valid.any():
        return 0.0
    values = values[valid]
    weights = weights[valid]
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cdf = np.cumsum(weights)
    cutoff = percentile / 100.0 * cdf[-1]
    return float(values[min(int(np.searchsorted(cdf, cutoff, side="left")), len(values) - 1)])


def nearest_support_labels(support: np.ndarray, labels: np.ndarray) -> np.ndarray:
    if not support.any():
        return np.zeros_like(labels)
    _, indices = ndi.distance_transform_edt(~support, return_indices=True)
    return labels[indices[0], indices[1]]


def build_component_donor(
    rgba: np.ndarray,
    signed_dist_px: np.ndarray,
    support: np.ndarray,
    donor_min_px: float,
    donor_max_px: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return linear-light donor RGB and masks, constrained per alpha component."""
    rgb_linear = srgb_to_linear(rgba[..., :3])
    labels, n = ndi.label(support, structure=np.ones((3, 3), dtype=bool))
    nearest_labels = nearest_support_labels(support, labels)
    donor_linear = np.zeros_like(rgb_linear, dtype=np.float32)
    donor_valid = np.zeros(support.shape, dtype=bool)
    global_core = support & (signed_dist_px >= max(1.0, donor_min_px))
    global_median = np.median(rgb_linear[global_core], axis=0) if global_core.any() else np.median(rgb_linear[support], axis=0) if support.any() else np.zeros(3)

    donor_ring_all = support & (signed_dist_px >= donor_min_px) & (signed_dist_px <= donor_max_px)
    if donor_ring_all.any():
        _, indices = ndi.distance_transform_edt(~donor_ring_all, return_indices=True)
        donor_linear = rgb_linear[indices[0], indices[1]].astype(np.float32)
        donor_labels = labels[indices[0], indices[1]]
        donor_valid = (nearest_labels > 0) & (donor_labels == nearest_labels)

    bad = nearest_labels > 0
    if donor_ring_all.any():
        bad &= ~donor_valid
    if bad.any() or not donor_ring_all.any():
        bad_labels = np.unique(nearest_labels[bad if donor_ring_all.any() else nearest_labels > 0])
        bad_labels = bad_labels[bad_labels != 0]
        for lbl in bad_labels:
            comp = labels == lbl
            if not comp.any():
                continue
            median_color = np.median(rgb_linear[comp], axis=0)
            target = nearest_labels == lbl
            donor_linear[target] = median_color
            donor_valid[target] = True

    donor_linear[nearest_labels == 0] = global_median
    donor_valid[nearest_labels > 0] = True
    return donor_linear, donor_valid, nearest_labels


def contour_mask(mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        return np.zeros_like(mask, dtype=bool)
    return mask ^ ndi.binary_erosion(mask, structure=np.ones((3, 3), dtype=bool))


def smooth_mask(mask: np.ndarray, radius_px: int) -> np.ndarray:
    if radius_px <= 0 or not mask.any():
        return mask
    selem = disk(radius_px)
    return ndi.binary_opening(ndi.binary_closing(mask, structure=selem), structure=selem)


def mask_perimeter(mask: np.ndarray) -> float:
    if not mask.any():
        return 0.0
    return float(measure_perimeter(mask.astype(bool), neighborhood=8))


def decide_three_zone(value: float, pass_max: float, fail_min: float, higher_is_bad: bool = True) -> str:
    if higher_is_bad:
        if value <= pass_max:
            return "PASS"
        if value >= fail_min:
            return "FAIL"
    else:
        if value >= pass_max:
            return "PASS"
        if value <= fail_min:
            return "FAIL"
    return "REVIEW"


def worst_verdict(verdicts: list[str]) -> str:
    if "FAIL" in verdicts:
        return "FAIL"
    if "REVIEW" in verdicts:
        return "REVIEW"
    return "PASS"


def d1_halo_gate(
    rgba: np.ndarray,
    out_dir: Path,
    mm_per_px: float | None,
    panels: list[tuple[int, int, int]],
    bg_color: tuple[int, int, int] | None,
) -> dict[str, Any]:
    cfg = CALIBRATION["D1_halo_gate"]
    alpha = rgba[..., 3].astype(np.float32) / 255.0
    signed_dist_px, support = support_signed_distance(alpha)
    if not support.any():
        return verdict_gate("D1_halo_gate", "PASS", {"support_px": 0})

    band_px = mm_to_px(float(cfg["band_mm"]), mm_per_px, fallback_px=3.0)
    donor_min_px = mm_to_px(float(cfg["donor_min_mm"]), mm_per_px, fallback_px=2.0)
    donor_max_px = mm_to_px(float(cfg["donor_max_mm"]), mm_per_px, fallback_px=5.0)
    edge_band = np.abs(signed_dist_px) <= band_px
    donor_linear, _donor_valid, _nearest_labels = build_component_donor(rgba, signed_dist_px, support, donor_min_px, donor_max_px)
    fg_linear = srgb_to_linear(rgba[..., :3])
    a = alpha[..., None]
    weights = np.clip(1.0 - (np.abs(signed_dist_px) / max(band_px, 1e-6)), 0.0, 1.0)

    panel_metrics: list[dict[str, Any]] = []
    worst_h_l = 0.0
    worst_area_px = 0
    offender = np.zeros(alpha.shape, dtype=bool)
    all_panels = list(DEFAULT_PANELS) + list(panels)
    for panel in all_panels:
        panel_linear = srgb_to_linear(np.array(panel, dtype=np.uint8).reshape(1, 1, 3))[0, 0]
        observed = a * fg_linear + (1.0 - a) * panel_linear
        donor_composite = a * donor_linear + (1.0 - a) * panel_linear
        h = np.maximum(0.0, lab_l_from_linear(observed) - lab_l_from_linear(donor_composite))
        h_vals = h[edge_band]
        w_vals = weights[edge_band]
        h_l = weighted_percentile(h_vals, w_vals, 95.0)
        hot = edge_band & (h > 3.0)
        area_px = int(hot.sum())
        if h_l > worst_h_l:
            worst_h_l = h_l
        if area_px > worst_area_px:
            worst_area_px = area_px
            offender = hot
        panel_metrics.append(
            {
                "panel": f"#{panel[0]:02X}{panel[1]:02X}{panel[2]:02X}",
                "weighted_p95_delta_l": round(h_l, 4),
                "area_px_delta_l_gt_3": area_px,
                "area_mm2_delta_l_gt_3": None if mm_per_px is None else round(float(area_px * mm_per_px * mm_per_px), 6),
            }
        )

    h_area_mm2 = px_area_to_mm2(worst_area_px, mm_per_px)
    h_key = None
    if bg_color is not None:
        bg_linear = srgb_to_linear(np.array(bg_color, dtype=np.uint8).reshape(1, 1, 3))[0, 0]
        denom = np.sum((bg_linear - donor_linear) ** 2, axis=2) + 1e-6
        pull = np.sum((fg_linear - donor_linear) * (bg_linear - donor_linear), axis=2) / denom
        h_key = weighted_percentile(np.maximum(0.0, pull)[edge_band], weights[edge_band], 95.0)

    if mm_per_px is None:
        verdict = "REVIEW" if worst_h_l > cfg["h_l_pass_max"] else "PASS"
    else:
        verdicts = [
            decide_three_zone(float(worst_h_l), float(cfg["h_l_pass_max"]), float(cfg["h_l_fail_min"])),
            decide_three_zone(float(h_area_mm2 or 0.0), float(cfg["h_area_pass_max_mm2"]), float(cfg["h_area_fail_min_mm2"])),
        ]
        if h_key is not None:
            verdicts.append(decide_three_zone(float(h_key), float(cfg["h_key_pass_max"]), float(cfg["h_key_fail_min"])))
        verdict = worst_verdict(verdicts)

    metric = {
        "support_px": int(support.sum()),
        "edge_band_px": int(edge_band.sum()),
        "band_mm": cfg["band_mm"] if mm_per_px is not None else None,
        "band_px": round(float(band_px), 3),
        "donor_inward_mm": [cfg["donor_min_mm"], cfg["donor_max_mm"]] if mm_per_px is not None else None,
        "donor_inward_px": [round(float(donor_min_px), 3), round(float(donor_max_px), 3)],
        "H_L": round(float(worst_h_l), 4),
        "H_area_px": int(worst_area_px),
        "H_area_mm2": None if h_area_mm2 is None else round(float(h_area_mm2), 6),
        "H_key": None if h_key is None else round(float(h_key), 4),
        "panels": panel_metrics,
        "physical_units": bool(mm_per_px is not None),
    }
    if mm_per_px is None:
        metric["units_advisory"] = "ppi/px-per-mm missing; D1 mm thresholds downgraded to REVIEW fallback"

    crop_paths = []
    if verdict != "PASS":
        crop = save_crop(rgba, offender if offender.any() else edge_band, out_dir, "D1_halo_gate", "edge-band")
        if crop:
            crop_paths.append(crop)
    return verdict_gate("D1_halo_gate", verdict, metric, crop_paths)


def d2_soft_alpha_fringe(
    rgba: np.ndarray,
    out_dir: Path,
    profile: str,
    mm_per_px: float | None,
    truth_rgba: np.ndarray | None = None,
) -> dict[str, Any]:
    cfg = CALIBRATION["D2_soft_alpha_fringe"]
    alpha = rgba[..., 3].astype(np.float32) / 255.0
    alpha_u8 = rgba[..., 3]
    fg_any = alpha_u8 > 0
    fg_opaque = alpha >= 0.5
    boundary = contour_mask(fg_opaque)
    soft = (alpha > 0.0) & (alpha < 1.0)
    soft_count = int(soft.sum())
    perimeter = int(boundary.sum())
    soft_ratio = float(soft_count / max(perimeter, 1))
    transition = (alpha > 0.10) & (alpha < 0.90)
    if transition.any():
        transition_width = ndi.distance_transform_edt(transition)
        p95_px = float(np.percentile(transition_width[transition], 95))
        max_width_px = float(transition_width[transition].max())
    else:
        p95_px = 0.0
        max_width_px = 0.0

    if truth_rgba is not None:
        truth_support = truth_rgba[..., 3].astype(np.float32) / 255.0 >= 0.5
        truth_contour = contour_mask(truth_support)
        if boundary.any() and truth_contour.any():
            dist_to_truth = ndi.distance_transform_edt(~truth_contour)
            dist_to_pred = ndi.distance_transform_edt(~boundary)
            pred_to_truth = dist_to_truth[boundary]
            truth_to_pred = dist_to_pred[truth_contour]
            contour_disp_p95_px = float(max(np.percentile(pred_to_truth, 95), np.percentile(truth_to_pred, 95)))
        else:
            contour_disp_p95_px = 0.0 if not boundary.any() and not truth_contour.any() else float(max(rgba.shape[:2]))
    else:
        contour_disp_p95_px = 0.0

    smooth_radius_px = max(1, int(round(mm_to_px(float(cfg["smooth_mm"]), mm_per_px, fallback_px=2.0))))
    raw_perimeter = mask_perimeter(fg_opaque)
    smooth_perimeter = mask_perimeter(smooth_mask(fg_opaque, smooth_radius_px))
    perimeter_excess = 0.0 if smooth_perimeter <= 0 else max(0.0, raw_perimeter / smooth_perimeter - 1.0)

    if mm_per_px is not None:
        w_p95_mm = p95_px * mm_per_px
        contour_disp_p95_mm = contour_disp_p95_px * mm_per_px
        verdicts = [
            decide_three_zone(w_p95_mm, float(cfg["w10_90_p95_pass_max_mm"]), float(cfg["w10_90_p95_fail_min_mm"])),
            decide_three_zone(
                contour_disp_p95_mm,
                float(cfg["contour_disp_p95_pass_max_mm"]),
                float(cfg["contour_disp_p95_fail_min_mm"]),
            ),
            decide_three_zone(perimeter_excess, float(cfg["perimeter_excess_pass_max"]), float(cfg["perimeter_excess_fail_min"])),
        ]
        if profile == "print" and soft_count > 0:
            verdicts.append("FAIL")
        verdict = worst_verdict(verdicts)
    else:
        ratio_thresh = cfg["soft_perimeter_ratio_max_print"] if profile == "print" else cfg["soft_perimeter_ratio_max_soft"]
        bad = soft_ratio > ratio_thresh or p95_px > cfg["transition_width_p95_max"] or (profile == "print" and soft_count > 0)
        verdict = "FAIL" if profile == "print" and soft_count > 0 else "REVIEW" if bad else "PASS"

    metric = {
        "soft_px": soft_count,
        "fg_nonzero_px": int(fg_any.sum()),
        "boundary_perimeter_px": perimeter,
        "soft_perimeter_ratio": round(soft_ratio, 4),
        "transition_width_p95_px": round(p95_px, 4),
        "transition_width_max_px": round(max_width_px, 4),
        "transition_width_p95_mm": None if mm_per_px is None else round(float(p95_px * mm_per_px), 6),
        "transition_width_max_mm": None if mm_per_px is None else round(float(max_width_px * mm_per_px), 6),
        "contour_displacement_p95_px": round(contour_disp_p95_px, 4),
        "contour_displacement_p95_mm": None if mm_per_px is None else round(float(contour_disp_p95_px * mm_per_px), 6),
        "perimeter_raw_px": round(raw_perimeter, 4),
        "perimeter_smooth_px": round(smooth_perimeter, 4),
        "perimeter_smooth_radius_px": smooth_radius_px,
        "perimeter_excess_ratio": round(perimeter_excess, 6),
        "profile": profile,
        "physical_units": bool(mm_per_px is not None),
    }
    crop_paths = []
    if verdict != "PASS":
        crop = save_crop(rgba, soft, out_dir, "D2_soft_alpha_fringe", "soft-alpha")
        if crop:
            crop_paths.append(crop)
    threshold = cfg.copy()
    threshold["active_soft_perimeter_ratio_max"] = cfg["soft_perimeter_ratio_max_print"] if profile == "print" else cfg["soft_perimeter_ratio_max_soft"]
    if mm_per_px is None:
        metric["units_advisory"] = "ppi/px-per-mm missing; D2 mm thresholds downgraded to REVIEW fallback"
    return verdict_gate("D2_soft_alpha_fringe", verdict, metric, crop_paths, threshold=threshold)


def border_connected(mask: np.ndarray) -> np.ndarray:
    labels, n = ndi.label(mask, structure=np.ones((3, 3), dtype=bool))
    if n == 0:
        return np.zeros_like(mask, dtype=bool)
    border_labels = np.unique(np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]))
    border_labels = border_labels[border_labels != 0]
    return np.isin(labels, border_labels)


def min_component_area_px(mm_per_px: float | None, cfg: dict[str, Any]) -> int:
    min_px = int(cfg["min_component_area_px"])
    if mm_per_px is None:
        return min_px
    min_mm_px = int(np.ceil(float(cfg["min_component_area_mm2"]) / (mm_per_px * mm_per_px)))
    return max(min_px, min_mm_px)


def d3a_alpha_pockets(rgba: np.ndarray, out_dir: Path, mm_per_px: float | None) -> dict[str, Any]:
    cfg = CALIBRATION["D3a_alpha_pockets"]
    alpha = rgba[..., 3]
    transparent = alpha == 0
    pockets = transparent & ~border_connected(transparent)
    labels, n = ndi.label(pockets, structure=np.ones((3, 3), dtype=bool))
    areas = [(lbl, int((labels == lbl).sum())) for lbl in range(1, n + 1)]
    min_area = min_component_area_px(mm_per_px, cfg)
    areas = [(lbl, area) for lbl, area in areas if area >= min_area]
    areas.sort(key=lambda item: item[1], reverse=True)
    total_area = int(sum(area for _lbl, area in areas))
    image_area = int(alpha.size)
    max_area = areas[0][1] if areas else 0
    count_per_mpx = float(len(areas) / max(image_area / 1_000_000.0, 1e-9))
    verdict = "REVIEW" if count_per_mpx > cfg["review_count_per_mpx_min"] else "PASS"
    metric = {
        "component_count": len(areas),
        "component_count_per_mpx": round(count_per_mpx, 4),
        "total_area_px": total_area,
        "max_area_px": max_area,
        "total_area_frac": round(float(total_area / max(image_area, 1)), 6),
        "max_area_frac": round(float(max_area / max(image_area, 1)), 6),
        "min_component_area_px": min_area,
        "min_component_area_mm2": None if mm_per_px is None else cfg["min_component_area_mm2"],
        "calibration_note": "alpha-zero pockets are advisory topology evidence; they never hard-fail approved art",
    }
    crop_paths = component_crops(rgba, labels, areas, out_dir, "D3a_alpha_pockets") if verdict != "PASS" else []
    return verdict_gate("D3a_alpha_pockets", verdict, metric, crop_paths)


def d3b_retained_background(
    rgba: np.ndarray,
    out_dir: Path,
    bg_color: tuple[int, int, int] | None,
) -> dict[str, Any]:
    cfg = CALIBRATION["D3b_retained_background"]
    if bg_color is None:
        metric = {
            "calibration_note": "D3b retained-background detection requires --bg-color; skipped without blocking",
        }
        return verdict_gate("D3b_retained_background", "PASS", metric, skipped_reason="--bg-color not provided")

    alpha = rgba[..., 3].astype(np.float32) / 255.0
    fg = alpha > 0.5
    lab = rgb2lab(rgba[..., :3].astype(np.float32) / 255.0)
    bg_lab = rgb2lab((np.array(bg_color, dtype=np.float32).reshape(1, 1, 3) / 255.0)).reshape(1, 1, 3)
    delta_e = deltaE_ciede2000(lab, bg_lab)
    retained = fg & (delta_e < float(cfg["tau_b_delta_e00"]))
    retained = retained & ~border_connected(retained)
    labels, n = ndi.label(retained, structure=np.ones((3, 3), dtype=bool))
    areas = [(lbl, int((labels == lbl).sum())) for lbl in range(1, n + 1)]
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
        "background_rgb": list(bg_color),
        "tau_b_delta_e00": cfg["tau_b_delta_e00"],
        "component_count": len(areas),
        "total_area_px": total_area,
        "max_area_px": max_area,
        "total_area_frac": round(float(total_area / max(image_area, 1)), 6),
        "max_area_frac": round(float(max_area / max(image_area, 1)), 6),
    }
    crop_paths = component_crops(rgba, labels, areas, out_dir, "D3b_retained_background") if not passed else []
    return verdict_gate("D3b_retained_background", "PASS" if passed else "FAIL", metric, crop_paths)


def load_aura_module():
    aura_path = REPO / "scripts" / "aura_gate.py"
    spec = importlib.util.spec_from_file_location("_gate_battery_aura_gate", aura_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {aura_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def d4_aura_gate(rgba_path: Path, rgba: np.ndarray, out_dir: Path, mm_per_px: float | None) -> dict[str, Any]:
    cfg = CALIBRATION["D4_aura_gate"]
    overlay_path = out_dir / "D4_aura_gate-overlay.png"
    alpha = rgba[..., 3].astype(np.float32) / 255.0
    lab = rgb2lab(rgba[..., :3].astype(np.float32) / 255.0)
    lstar = lab[..., 0]
    chroma = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
    local_mean = ndi.uniform_filter(lstar.astype(np.float32), size=5)
    local_sq_mean = ndi.uniform_filter((lstar.astype(np.float32) ** 2), size=5)
    local_std = np.sqrt(np.maximum(0.0, local_sq_mean - local_mean**2))
    opaque = alpha >= 0.90
    material_core = opaque & ((chroma >= 10.0) | (lstar <= 80.0) | (local_std >= 2.0))
    if material_core.any():
        dist_out_px = ndi.distance_transform_edt(~material_core)
        shell_min_px = mm_to_px(float(cfg["shell_min_mm"]), mm_per_px, fallback_px=1.0)
        shell_max_px = mm_to_px(float(cfg["shell_max_mm"]), mm_per_px, fallback_px=10.0)
        shell_zone = (~material_core) & (dist_out_px >= shell_min_px) & (dist_out_px <= shell_max_px)
        shell = shell_zone & opaque & (lstar > cfg["shell_l_min"]) & (chroma < cfg["shell_chroma_max"]) & (local_std < cfg["shell_texture_std_max"])
        core_boundary = contour_mask(material_core)
        wrapped_boundary = core_boundary & ndi.binary_dilation(shell, structure=disk(max(1, int(round(shell_max_px)))))
        wrap_fraction = float(wrapped_boundary.sum() / max(core_boundary.sum(), 1))
        if shell.any():
            shell_width_px = dist_out_px[shell]
            median_width_px = float(np.median(shell_width_px))
            p95_width_px = float(np.percentile(shell_width_px, 95))
        else:
            median_width_px = 0.0
            p95_width_px = 0.0
    else:
        shell = np.zeros(alpha.shape, dtype=bool)
        wrap_fraction = 0.0
        median_width_px = 0.0
        p95_width_px = 0.0
        shell_min_px = mm_to_px(float(cfg["shell_min_mm"]), mm_per_px, fallback_px=1.0)
        shell_max_px = mm_to_px(float(cfg["shell_max_mm"]), mm_per_px, fallback_px=10.0)

    shell_metric = {
        "shell_px": int(shell.sum()),
        "shell_area_mm2": None if mm_per_px is None else round(float(shell.sum() * mm_per_px * mm_per_px), 6),
        "wrap_fraction": round(wrap_fraction, 6),
        "shell_width_median_px": round(median_width_px, 4),
        "shell_width_p95_px": round(p95_width_px, 4),
        "shell_width_median_mm": None if mm_per_px is None else round(float(median_width_px * mm_per_px), 6),
        "shell_width_p95_mm": None if mm_per_px is None else round(float(p95_width_px * mm_per_px), 6),
        "shell_range_px": [round(float(shell_min_px), 3), round(float(shell_max_px), 3)],
        "physical_units": bool(mm_per_px is not None),
    }
    shell_verdict = "PASS"
    median_width_mm = median_width_px * mm_per_px if mm_per_px is not None else None
    if mm_per_px is None:
        if wrap_fraction >= cfg["wrap_fraction_review_min"] and median_width_px >= 2.0:
            shell_verdict = "REVIEW"
        shell_metric["units_advisory"] = "ppi/px-per-mm missing; D4 shell-width mm thresholds downgraded to REVIEW fallback"
    elif wrap_fraction >= cfg["wrap_fraction_fail_min"] and (median_width_mm or 0.0) >= cfg["median_width_fail_min_mm"]:
        shell_verdict = "FAIL"
    elif wrap_fraction >= cfg["wrap_fraction_review_min"] and (median_width_mm or 0.0) >= cfg["median_width_review_min_mm"]:
        shell_verdict = "REVIEW"

    try:
        aura_gate = load_aura_module()
        result = aura_gate.score_image(rgba_path, overlay_path=overlay_path, fail_thresh=cfg["aura_index_max"])
        metric = {"shell_geometry": shell_metric, "aura_gate_secondary": result}
        verdict = shell_verdict
        crop_paths = []
        if verdict != "PASS":
            crop = save_crop(rgba, shell if shell.any() else (alpha > 0), out_dir, "D4_aura_gate", "shell")
            if crop:
                crop_paths.append(crop)
            if overlay_path.exists():
                crop_paths.append(str(overlay_path))
        return verdict_gate("D4_aura_gate", verdict, metric, crop_paths)
    except Exception as exc:  # pragma: no cover - defensive: reports rather than hiding D4 failure.
        metric = {"shell_geometry": shell_metric, "aura_gate_secondary": {"error": str(exc)}}
        return verdict_gate("D4_aura_gate", worst_verdict([shell_verdict, "REVIEW"]), metric)


def d5_hole_gate(
    rgba: np.ndarray,
    source_path: Path | None,
    truth_path: Path | None,
    bg: tuple[int, int, int] | None,
    out_dir: Path,
    mm_per_px: float | None,
) -> dict[str, Any]:
    cfg = CALIBRATION["D5_hole_gate"]
    if truth_path is not None:
        truth = np.asarray(Image.open(truth_path).convert("RGBA"))
        if truth.shape[:2] != rgba.shape[:2]:
            raise ValueError(f"--truth size {truth.shape[:2]} does not match --rgba size {rgba.shape[:2]}")
        pred_a = rgba[..., 3].astype(np.float32) / 255.0
        truth_a = truth[..., 3].astype(np.float32) / 255.0
        truth_support = truth_a > 0.01
        labels, n = ndi.label(truth_support, structure=np.ones((3, 3), dtype=bool))
        if n == 0:
            return verdict_gate("D5_hole_gate", "PASS", {"mode": "truth", "truth_components": 0})
        edt_px = ndi.distance_transform_edt(truth_support)
        mm_scale = mm_per_px if mm_per_px is not None else 1.0
        thickness = 2.0 * edt_px * mm_scale
        lab = rgb2lab(truth[..., :3].astype(np.float32) / 255.0)
        chroma = np.sqrt(lab[..., 1] ** 2 + lab[..., 2] ** 2)
        pale = (lab[..., 0] > 85.0) & (chroma < 10.0)
        bins = {
            "lt_0_20mm": truth_support & (thickness < cfg["thin_bin_max_mm"]),
            "0_20_0_50mm": truth_support & (thickness >= cfg["thin_bin_max_mm"]) & (thickness <= cfg["medium_bin_max_mm"]),
            "gt_0_50mm": truth_support & (thickness > cfg["medium_bin_max_mm"]),
            "pale_l_gt_85_c_lt_10": truth_support & pale,
        }
        recalls: list[float] = []
        component_metrics: list[dict[str, Any]] = []
        skeleton_breaks = 0
        survived = 0
        for lbl in range(1, n + 1):
            comp = labels == lbl
            if not comp.any():
                continue
            comp_survives = bool(np.max(pred_a[comp]) > 0.05)
            survived += int(comp_survives)
            skel = skeletonize(comp)
            breaks = int((skel & (pred_a < 0.05)).sum())
            skeleton_breaks += breaks
            per_bin: dict[str, float | None] = {}
            for name, bin_mask in bins.items():
                q = comp & bin_mask
                denom = float(truth_a[q].sum())
                if denom <= 0.0:
                    per_bin[name] = None
                    continue
                recall = float(np.minimum(pred_a[q], truth_a[q]).sum() / denom)
                per_bin[name] = round(recall, 6)
                recalls.append(recall)
            denom_all = float(truth_a[comp].sum())
            recall_all = float(np.minimum(pred_a[comp], truth_a[comp]).sum() / max(denom_all, 1e-6))
            recalls.append(recall_all)
            component_metrics.append(
                {
                    "label": lbl,
                    "area_px": int(comp.sum()),
                    "recall_all": round(recall_all, 6),
                    "recall_by_stratum": per_bin,
                    "survived": comp_survives,
                    "skeleton_break_px": breaks,
                }
            )
        recalls_arr = np.array(recalls, dtype=np.float32) if recalls else np.array([1.0], dtype=np.float32)
        min_recall = float(np.min(recalls_arr))
        p5_recall = float(np.percentile(recalls_arr, 5))
        survival = float(survived / max(n, 1))
        verdicts = [
            decide_three_zone(min_recall, float(cfg["truth_recall_pass_min"]), float(cfg["truth_recall_fail_below"]), higher_is_bad=False),
            decide_three_zone(survival, float(cfg["truth_component_survival_pass_min"]), float(cfg["truth_component_survival_fail_below"]), higher_is_bad=False),
            "PASS" if skeleton_breaks <= cfg["truth_skeleton_breaks_pass_max"] else "FAIL",
        ]
        verdict = worst_verdict(verdicts)
        deleted = truth_support & (pred_a < np.minimum(0.05, truth_a * 0.25))
        crop_paths = component_crops(rgba, labels, [(item["label"], item["area_px"]) for item in component_metrics if not item["survived"]], out_dir, "D5_hole_gate")
        if verdict != "PASS" and not crop_paths:
            crop = save_crop(rgba, deleted if deleted.any() else truth_support, out_dir, "D5_hole_gate", "truth-recall")
            if crop:
                crop_paths.append(crop)
        metric = {
            "mode": "truth",
            "truth_components": int(n),
            "component_survival": round(survival, 6),
            "recall_min": round(min_recall, 6),
            "recall_p5": round(p5_recall, 6),
            "skeleton_break_px": skeleton_breaks,
            "thickness_units": "mm" if mm_per_px is not None else "px_fallback",
            "physical_units": bool(mm_per_px is not None),
            "worst_components": sorted(component_metrics, key=lambda item: item["recall_all"])[:5],
        }
        if mm_per_px is None:
            metric["units_advisory"] = "ppi/px-per-mm missing; thickness bins are px fallback and D5 truth verdict is conservative"
            verdict = worst_verdict([verdict, "REVIEW"]) if verdict == "PASS" else verdict
        return verdict_gate("D5_hole_gate", verdict, metric, crop_paths)

    if source_path is None:
        return empty_gate("D5_hole_gate", "--truth/--source not provided")
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
    suspicious = deleted_frac > cfg["deleted_area_frac_max"] or max_area > cfg["deleted_component_area_max"]
    metric = {
        "mode": "source_heuristic",
        "background_rgb": [int(x) for x in bg_rgb],
        "expected_fg_px": expected_area,
        "deleted_art_px": deleted_area,
        "deleted_area_frac_of_expected": round(deleted_frac, 6),
        "deleted_component_count": len(areas),
        "deleted_component_max_area_px": max_area,
        "strata": strata,
        "worst_components": comp_metrics[:5],
        "calibration_note": "source/background heuristic is REVIEW-only; use --truth for blocking recall",
    }
    verdict = "REVIEW" if suspicious else "PASS"
    crop_paths = component_crops(rgba, labels, areas, out_dir, "D5_hole_gate") if suspicious else []
    return verdict_gate("D5_hole_gate", verdict, metric, crop_paths)


def d6_spill_gate(rgba: np.ndarray, bg: tuple[int, int, int] | None, out_dir: Path, mm_per_px: float | None) -> dict[str, Any]:
    cfg = CALIBRATION["D6_spill_gate"]
    if bg is None:
        return empty_gate("D6_spill_gate", "--bg-color not provided")
    alpha = rgba[..., 3].astype(np.float32) / 255.0
    signed_dist_px, support = support_signed_distance(alpha)
    if support.sum() < 25:
        return empty_gate("D6_spill_gate", "insufficient foreground pixels")
    band_px = mm_to_px(float(cfg["band_mm"]), mm_per_px, fallback_px=4.0)
    donor_min_px = mm_to_px(0.15, mm_per_px, fallback_px=2.0)
    donor_max_px = mm_to_px(0.35, mm_per_px, fallback_px=5.0)
    transition = (alpha > 0.02) & (alpha < 0.95) & (np.abs(signed_dist_px) <= band_px)
    if transition.sum() < 25:
        return empty_gate("D6_spill_gate", "insufficient transition-band pixels")
    donor_linear, _donor_valid, _nearest_labels = build_component_donor(rgba, signed_dist_px, support, donor_min_px, donor_max_px)
    donor_srgb = np.clip(np.round(linear_to_srgb(donor_linear) * 255.0), 0, 255).astype(np.uint8)
    fg_oklab = rgb_to_oklab(rgba[..., :3])
    donor_oklab = rgb_to_oklab(donor_srgb)
    bg_ab = rgb_to_oklab(np.array(bg, dtype=np.uint8).reshape(1, 1, 3))[0, 0, 1:3]
    bg_norm = float(np.linalg.norm(bg_ab))
    k = np.zeros(2, dtype=np.float32) if bg_norm == 0.0 else (bg_ab / bg_norm).astype(np.float32)
    raw_projection = np.sum((fg_oklab[..., 1:3] - donor_oklab[..., 1:3]) * k, axis=2)
    excess = np.maximum(0.0, raw_projection - float(cfg["tau_clean"]))
    vals = excess[transition]
    p95 = float(np.percentile(vals, 95)) if vals.size else 0.0
    max_excess = float(vals.max()) if vals.size else 0.0
    hot = transition & (excess > cfg["spill_review_min"])
    area_px = int(hot.sum())
    area_mm2 = px_area_to_mm2(area_px, mm_per_px)
    suspicious = p95 > cfg["spill_p95_pass_max"] or (area_mm2 is not None and area_mm2 > cfg["spill_area_review_min_mm2"])
    verdict = "REVIEW" if suspicious else "PASS"
    metric = {
        "background_rgb": list(bg),
        "transition_band_px": int(transition.sum()),
        "band_mm": cfg["band_mm"] if mm_per_px is not None else None,
        "band_px": round(float(band_px), 3),
        "tau_clean": cfg["tau_clean"],
        "key_direction_ab": [round(float(x), 6) for x in k],
        "spill_excess_p95": round(p95, 6),
        "spill_excess_max": round(max_excess, 6),
        "spill_area_px": area_px,
        "spill_area_mm2": None if area_mm2 is None else round(float(area_mm2), 6),
        "calibration_note": "D6 remains REVIEW-only until clean-edge tau is calibrated",
        "physical_units": bool(mm_per_px is not None),
    }
    if mm_per_px is None:
        metric["units_advisory"] = "ppi/px-per-mm missing; D6 area threshold downgraded to REVIEW fallback"
    crop_paths = []
    if verdict != "PASS":
        heat = np.zeros((*alpha.shape, 4), dtype=np.uint8)
        heat[..., 0] = np.clip(excess / max(float(cfg["spill_review_min"]), 1e-6) * 255.0, 0, 255).astype(np.uint8)
        heat[..., 3] = np.where(transition, 255, 0).astype(np.uint8)
        heat_path = out_dir / "D6_spill_gate-heatmap.png"
        out_dir.mkdir(parents=True, exist_ok=True)
        Image.fromarray(heat, "RGBA").save(heat_path)
        crop_paths.append(str(heat_path))
        crop = save_crop(rgba, hot if hot.any() else transition, out_dir, "D6_spill_gate", "edge-band")
        if crop:
            crop_paths.append(crop)
    return verdict_gate("D6_spill_gate", verdict, metric, crop_paths)


def d7_border_gate(rgba: np.ndarray, out_dir: Path, border_policy: str) -> dict[str, Any]:
    cfg = CALIBRATION["D7_border_gate"]
    if border_policy not in {"forbid", "allow", "auto"}:
        raise ValueError(f"invalid border policy {border_policy!r}")
    alpha = rgba[..., 3]
    strip = int(cfg["strip_px"])
    border = np.zeros(alpha.shape, dtype=bool)
    border[:strip, :] = True
    border[-strip:, :] = True
    border[:, :strip] = True
    border[:, -strip:] = True
    occupied = border & (alpha > 0)
    occupancy = float(occupied.sum() / max(border.sum(), 1))
    occupied_border = occupancy > cfg["border_alpha_occupancy_max"]
    if border_policy == "forbid":
        verdict = "FAIL" if occupied_border else "PASS"
    elif border_policy == "auto":
        verdict = "REVIEW" if occupied_border else "PASS"
    else:
        verdict = "PASS"
    metric = {
        "border_policy": border_policy,
        "strip_px": strip,
        "border_px": int(border.sum()),
        "occupied_px": int(occupied.sum()),
        "border_alpha_occupancy": round(occupancy, 8),
        "calibration_note": "auto reviews edge occupancy for full-bleed wrapper art; forbid hard-fails isolated-subject edge crops",
    }
    crop_paths = []
    if verdict != "PASS":
        crop = save_crop(rgba, occupied, out_dir, "D7_border_gate", "occupied-border", pad=8)
        if crop:
            crop_paths.append(crop)
    threshold = cfg.copy()
    threshold["border_policy"] = border_policy
    return verdict_gate("D7_border_gate", verdict, metric, crop_paths, threshold=threshold)


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
    return verdict_gate("D8_alpha_sanity", "PASS" if passed else "FAIL", metric, crop_paths)


def run_battery(
    rgba_path: Path,
    source_path: Path | None,
    truth_path: Path | None,
    bg_color: tuple[int, int, int] | None,
    profile: str,
    out_dir: Path,
    ppi: float | None = None,
    px_per_mm: float | None = None,
    panels: list[tuple[int, int, int]] | None = None,
    border_policy: str = "auto",
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rgba = load_rgba(rgba_path)
    truth_rgba = load_rgba(truth_path) if truth_path is not None else None
    mm_per_px, unit_info = mm_per_px_from_args(ppi, px_per_mm)
    gates = {
        "D1_halo_gate": d1_halo_gate(rgba, out_dir, mm_per_px, panels or [], bg_color),
        "D2_soft_alpha_fringe": d2_soft_alpha_fringe(rgba, out_dir, profile, mm_per_px, truth_rgba),
        "D3a_alpha_pockets": d3a_alpha_pockets(rgba, out_dir, mm_per_px),
        "D3b_retained_background": d3b_retained_background(rgba, out_dir, bg_color),
        "D4_aura_gate": d4_aura_gate(rgba_path, rgba, out_dir, mm_per_px),
        "D5_hole_gate": d5_hole_gate(rgba, source_path, truth_path, bg_color, out_dir, mm_per_px),
        "D6_spill_gate": d6_spill_gate(rgba, bg_color, out_dir, mm_per_px),
        "D7_border_gate": d7_border_gate(rgba, out_dir, border_policy),
        "D8_alpha_sanity": d8_alpha_sanity(rgba, out_dir),
    }
    overall_verdict = worst_verdict([gate["verdict"] for gate in gates.values()])
    exit_code = 0 if overall_verdict == "PASS" else 2 if overall_verdict == "FAIL" else 3
    weak_agent_report = [
        {
            "gate": name,
            "verdict": gate["verdict"],
            "prescribed_action": PRESCRIBED_ACTIONS[name],
            "agent_instruction": "Do not reinterpret raw metrics; follow the prescribed action for this defect class.",
        }
        for name, gate in gates.items()
        if gate["verdict"] != "PASS"
    ]
    battery = {
        "version": 3,
        "rgba": str(rgba_path),
        "source": str(source_path) if source_path else None,
        "truth": str(truth_path) if truth_path else None,
        "bg_color": f"#{bg_color[0]:02X}{bg_color[1]:02X}{bg_color[2]:02X}" if bg_color else None,
        "profile": profile,
        "border_policy": border_policy,
        "units": unit_info,
        "panels": [f"#{p[0]:02X}{p[1]:02X}{p[2]:02X}" for p in list(DEFAULT_PANELS) + list(panels or [])],
        "verdict": overall_verdict,
        "exit_code": exit_code,
        "pass": overall_verdict == "PASS",
        "gates": gates,
        "weak_agent_report": weak_agent_report,
    }
    (out_dir / "battery.json").write_text(json.dumps(battery, indent=2))
    return battery


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rgba", required=True, type=Path)
    ap.add_argument("--source", type=Path, default=None)
    ap.add_argument("--truth", type=Path, default=None, help="Trusted RGBA reference for D2 contour and D5 recall metrics")
    ap.add_argument("--bg-color", type=parse_hex_color, default=None)
    ap.add_argument("--panels", type=parse_panel_list, default=None, help="Comma-separated #RRGGBB panel colors added to D1 panel set")
    ap.add_argument("--ppi", type=float, default=None, help="Final pixels per inch for physical gate thresholds")
    ap.add_argument("--px-per-mm", type=float, default=None, help="Final pixels per millimeter for physical gate thresholds")
    ap.add_argument("--profile", choices=("print", "soft"), default="soft")
    ap.add_argument("--border-policy", choices=("forbid", "allow", "auto"), default="auto")
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args(argv)

    battery = run_battery(
        args.rgba,
        args.source,
        args.truth,
        args.bg_color,
        args.profile,
        args.out_dir,
        ppi=args.ppi,
        px_per_mm=args.px_per_mm,
        panels=args.panels or [],
        border_policy=args.border_policy,
    )
    print(
        json.dumps(
            {
                "verdict": battery["verdict"],
                "pass": battery["pass"],
                "exit_code": battery["exit_code"],
                "battery_json": str(args.out_dir / "battery.json"),
            },
            indent=2,
        )
    )
    return int(battery["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
