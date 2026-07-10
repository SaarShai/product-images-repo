#!/usr/bin/env python3
"""Review-trigger scanner for watercolor background-removal defects.

This is a TRIAGE tool, not a certification gate.  It flags candidates that
have no frozen benchmark guard (see ``bg-benchmark/``) so a human can look at
the right crops fast.  It never blocks: the process exits 0 unless an actual
I/O error prevents it from reading inputs or writing outputs.

Three defect classes are scanned, each measured against a per-image PAPER
FIELD estimated from the SOURCE alone (before the candidate is ever opened):

1. MATTE-RIM (white/paper-colored fringe stuck at the alpha boundary that is
   not simply the soft edge of real paint).
2. VANISHED-COMPONENT (coherent painted content in the source whose alpha
   collapsed to near-zero in the candidate).
3. HOLE CENSUS (enclosed paper wrongly kept opaque, or enclosed painted
   content wrongly carved into a transparent hole), tracked across an alpha
   threshold sweep so persistence (not just one lucky cut) drives severity.

Every detector reports facts (bbox/area/severity/detail); ranking across
detectors is a rough common currency (area x confidence) for the review
sheet only, not a verdict.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi


Image.MAX_IMAGE_PIXELS = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TriageConfig:
    # Paper-field estimation (source only, before the candidate is opened).
    paper_border_delta_e_tol: float = 20.0
    paper_delta_e_paper_like: float = 10.0
    paper_delta_e_strong_paint: float = 30.0

    # Matte-rim (white/paper fringe) detector.
    matte_rim_alpha_min: int = 16
    matte_rim_alpha_max: int = 255
    matte_rim_edge_band_px: int = 3
    matte_rim_donor_radius_px: int = 8
    matte_rim_donor_alpha_min: int = 240
    matte_rim_alpha_sweep_thresholds: Tuple[int, ...] = (16, 128, 224)

    # Vanished-component (deleted pale paint) detector.  Calibrated down from
    # an initial 64px: real known-deleted pale/translucent bubbles on
    # image14 were as small as ~41px of qualifying evidence.
    vanished_min_area_px: int = 24
    vanished_collapse_alpha_max: int = 32
    vanished_blur_sigmas: Tuple[float, ...] = (0.0, 1.5, 3.0)
    vanished_attachment_radius_px: int = 5

    # Hole census (enclosed paper retained / wrongly opened) detector.
    hole_census_alpha_thresholds: Tuple[int, ...] = (8, 32, 128, 224)
    hole_census_min_area_px: int = 16
    hole_census_max_absolute_fg_area_px: int = 20000
    hole_census_paperlike_fraction: float = 0.5

    # Tile-level source-on-paper reconstruction.
    recon_tile_px: int = 128
    recon_tile_p99_flag_8bit: float = 20.0

    # Review sheet.
    review_top_n: int = 12
    review_clean_crops: int = 3
    review_crop_px: int = 160
    review_seed: int = 0

    def validate(self) -> None:
        if self.paper_delta_e_paper_like <= 0:
            raise ValueError("paper_delta_e_paper_like must be positive")
        if not 0 <= self.matte_rim_alpha_min < self.matte_rim_alpha_max <= 255:
            raise ValueError("matte-rim alpha band is invalid")
        if self.vanished_min_area_px <= 0 or self.hole_census_min_area_px <= 0:
            raise ValueError("minimum areas must be positive")
        if self.recon_tile_px <= 0:
            raise ValueError("reconstruction tile size must be positive")


# ---------------------------------------------------------------------------
# Colour helpers (self-contained sRGB -> CIE Lab; numpy only, no new deps)
# ---------------------------------------------------------------------------


def rgb_to_lab(rgb01: np.ndarray) -> np.ndarray:
    """Convert sRGB [0,1] (any leading shape, last axis 3) to CIE Lab (D65)."""
    rgb = np.clip(np.asarray(rgb01, dtype=np.float64), 0.0, 1.0)
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    matrix = np.array(
        [
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041],
        ]
    )
    xyz = linear @ matrix.T
    white = np.array([0.95047, 1.0, 1.08883])
    xyz_normalized = xyz / white
    delta = 6.0 / 29.0
    f = np.where(
        xyz_normalized > delta**3,
        np.cbrt(xyz_normalized),
        xyz_normalized / (3 * delta**2) + 4.0 / 29.0,
    )
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    lightness = 116.0 * fy - 16.0
    a_axis = 500.0 * (fx - fy)
    b_axis = 200.0 * (fy - fz)
    return np.stack([lightness, a_axis, b_axis], axis=-1)


def delta_e76(lab_a: np.ndarray, lab_b: np.ndarray) -> np.ndarray:
    return np.sqrt(np.sum((np.asarray(lab_a) - np.asarray(lab_b)) ** 2, axis=-1))


# ---------------------------------------------------------------------------
# Small morphology helpers (duplicated locally to keep this tool standalone)
# ---------------------------------------------------------------------------


def _disk(radius: int) -> np.ndarray:
    if radius <= 0:
        return np.ones((1, 1), dtype=bool)
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (xx * xx + yy * yy) <= radius * radius


def _erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    return ndi.binary_erosion(mask, structure=_disk(radius), border_value=0)


def _dilate(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return mask.copy()
    return ndi.binary_dilation(mask, structure=_disk(radius), border_value=0)


_FULL_CONNECTIVITY = np.ones((3, 3), dtype=bool)


def _label_components(mask: np.ndarray) -> list[dict[str, Any]]:
    labeled, _ = ndi.label(mask, structure=_FULL_CONNECTIVITY)
    h, w = mask.shape
    components: list[dict[str, Any]] = []
    for label_id, obj_slice in enumerate(ndi.find_objects(labeled), start=1):
        if obj_slice is None:
            continue
        mask_local = labeled[obj_slice] == label_id
        area = int(mask_local.sum())
        y0, y1 = obj_slice[0].start, obj_slice[0].stop
        x0, x1 = obj_slice[1].start, obj_slice[1].stop
        touches_border = y0 == 0 or x0 == 0 or y1 == h or x1 == w
        components.append(
            {
                "label_id": label_id,
                "slice": obj_slice,
                "mask_local": mask_local,
                "area": area,
                "bbox": (x0, y0, x1, y1),
                "touches_border": touches_border,
            }
        )
    return components


# ---------------------------------------------------------------------------
# Paper field: estimated from the SOURCE alone, before the candidate is read
# ---------------------------------------------------------------------------


def _polynomial_features(xn: np.ndarray, yn: np.ndarray, degree: int) -> np.ndarray:
    ones = np.ones_like(xn)
    terms = [ones, xn, yn]
    if degree >= 2:
        terms.extend([xn * xn, xn * yn, yn * yn])
    return np.stack(terms, axis=-1)


def _border_patch_mask(lab: np.ndarray, tol: float) -> np.ndarray:
    """Border-connected paper-like region of the SOURCE, via a seeded flood.

    This never looks at the candidate.  A generous Lab tolerance from the
    border median admits gentle lighting gradients; only components that
    actually touch the image border are kept, so isolated paper-colored
    foreground never leaks in.
    """
    h, w = lab.shape[:2]
    border_lab = np.concatenate(
        [lab[0, :, :], lab[-1, :, :], lab[:, 0, :], lab[:, -1, :]], axis=0
    )
    seed = np.median(border_lab, axis=0)
    paperish = delta_e76(lab, seed[None, None, :]) < tol
    labeled, n = ndi.label(paperish, structure=_FULL_CONNECTIVITY)
    if n == 0:
        return np.zeros((h, w), dtype=bool)
    border_labels: set[int] = set()
    border_labels |= set(int(v) for v in labeled[0, :].tolist())
    border_labels |= set(int(v) for v in labeled[-1, :].tolist())
    border_labels |= set(int(v) for v in labeled[:, 0].tolist())
    border_labels |= set(int(v) for v in labeled[:, -1].tolist())
    border_labels.discard(0)
    if not border_labels:
        return np.zeros((h, w), dtype=bool)
    return np.isin(labeled, np.fromiter(border_labels, dtype=labeled.dtype))


@dataclass
class PaperField:
    degree: int
    coeffs: Any  # np.ndarray, shape (terms, 3); JSON-safe conversion happens on export
    height: int
    width: int
    patch_pixels: int
    low_confidence: bool
    residual_rgb_8bit_p50_p95_p99: list
    residual_delta_e_p50_p95_p99: list

    def evaluate(self) -> np.ndarray:
        yy, xx = np.mgrid[0 : self.height, 0 : self.width]
        xn = xx.astype(np.float64) / max(self.width - 1, 1) * 2 - 1
        yn = yy.astype(np.float64) / max(self.height - 1, 1) * 2 - 1
        features = _polynomial_features(xn, yn, self.degree)
        field_rgb = np.tensordot(features, np.asarray(self.coeffs), axes=([2], [0]))
        return np.clip(field_rgb, 0.0, 1.0).astype(np.float32)


def fit_paper_field(source_rgb01: np.ndarray, config: TriageConfig) -> PaperField:
    """Estimate a per-image paper model from SOURCE border/exterior patches.

    Robust median seed -> border-connected patch mask -> low-order 2D
    polynomial gradient fit per channel.  Degree scales with how much patch
    evidence is available; a starved patch (e.g. artwork touching every
    edge) falls back to the literal outer ring and is marked low_confidence.
    """
    h, w = source_rgb01.shape[:2]
    lab = rgb_to_lab(source_rgb01)
    patch_mask = _border_patch_mask(lab, config.paper_border_delta_e_tol)
    low_confidence = False
    min_patch_px = max(8, h + w)
    if int(patch_mask.sum()) < min_patch_px:
        ring = np.zeros((h, w), dtype=bool)
        ring[0, :] = True
        ring[-1, :] = True
        ring[:, 0] = True
        ring[:, -1] = True
        patch_mask = ring
        low_confidence = True

    ys, xs = np.nonzero(patch_mask)
    patch_pixels = int(len(xs))
    if patch_pixels < 4:
        raise ValueError("could not find any paper/border evidence in the source")
    xn = xs.astype(np.float64) / max(w - 1, 1) * 2 - 1
    yn = ys.astype(np.float64) / max(h - 1, 1) * 2 - 1
    if patch_pixels >= 5000:
        degree = 2
    elif patch_pixels >= 50:
        degree = 1
    else:
        degree = 0
        low_confidence = True

    features = _polynomial_features(xn, yn, degree)
    values = source_rgb01[ys, xs, :].astype(np.float64)
    coeffs, *_ = np.linalg.lstsq(features, values, rcond=None)
    predicted = features @ coeffs

    residual_rgb_8bit = np.abs(values - predicted) * 255.0
    residual_percentiles_rgb = [
        float(np.percentile(residual_rgb_8bit, p)) for p in (50, 95, 99)
    ]
    predicted_lab = rgb_to_lab(np.clip(predicted, 0.0, 1.0))
    values_lab = rgb_to_lab(values)
    residual_delta_e = delta_e76(values_lab, predicted_lab)
    residual_percentiles_delta_e = [
        float(np.percentile(residual_delta_e, p)) for p in (50, 95, 99)
    ]

    return PaperField(
        degree=degree,
        coeffs=coeffs,
        height=h,
        width=w,
        patch_pixels=patch_pixels,
        low_confidence=low_confidence,
        residual_rgb_8bit_p50_p95_p99=residual_percentiles_rgb,
        residual_delta_e_p50_p95_p99=residual_percentiles_delta_e,
    )


# ---------------------------------------------------------------------------
# Suspects
# ---------------------------------------------------------------------------


@dataclass
class Suspect:
    kind: str
    bbox: list  # [x0, y0, x1, y1] in source-resolution pixel coordinates
    area: int
    severity: float
    detail: dict


# ---------------------------------------------------------------------------
# Detector 2: MATTE-RIM (white/paper-colored fringe)
# ---------------------------------------------------------------------------


def detect_matte_rim(
    source_lab: np.ndarray,
    candidate_rgb01: np.ndarray,
    candidate_alpha_u8: np.ndarray,
    paper_field_lab: np.ndarray,
    config: TriageConfig,
) -> Tuple[list[Suspect], dict[str, int]]:
    """Flag retained candidate opacity that has no real-paint basis in SOURCE.

    The primary gate compares BOTH the candidate's straight RGB and the
    SOURCE pixel at the same location against the local paper field: a
    boundary-band pixel that is paper-like in the candidate AND whose true
    source is also paper-like has no legitimate paint underneath it at all,
    so any alpha kept there is a matte-rim artifact, not a soft wash edge (a
    real translucent wash has non-paper-like SOURCE evidence even though its
    candidate alpha is low).  A same-component colorful high-alpha "donor"
    search is kept as an auxiliary confidence signal only: for realistic
    fringes attached directly to the true object, a donor is nearly always
    within reach, so gating on donor-absence alone (as first drafted here)
    almost never fires and was corrected during calibration.
    """
    alpha = candidate_alpha_u8.astype(np.int32)
    h, w = alpha.shape
    fg_reference = alpha >= 128
    edge_band = _dilate(fg_reference, config.matte_rim_edge_band_px) & ~_erode(
        fg_reference, config.matte_rim_edge_band_px
    )
    boundary_band = (
        edge_band
        & (alpha >= config.matte_rim_alpha_min)
        & (alpha <= config.matte_rim_alpha_max)
    )

    candidate_lab = rgb_to_lab(candidate_rgb01)
    delta_to_paper = delta_e76(candidate_lab, paper_field_lab)
    paper_like = delta_to_paper < config.paper_delta_e_paper_like
    source_delta_to_paper = delta_e76(source_lab, paper_field_lab)
    source_paper_like = source_delta_to_paper < config.paper_delta_e_paper_like

    component_mask = alpha > config.matte_rim_alpha_min
    labeled, _ = ndi.label(component_mask, structure=_FULL_CONNECTIVITY)
    colorful_high_alpha = (alpha >= config.matte_rim_donor_alpha_min) & (
        delta_to_paper >= config.paper_delta_e_paper_like
    )

    has_donor = np.zeros_like(boundary_band)
    pad = config.matte_rim_donor_radius_px
    for label_id, obj_slice in enumerate(ndi.find_objects(labeled), start=1):
        if obj_slice is None:
            continue
        y0, y1 = obj_slice[0].start, obj_slice[0].stop
        x0, x1 = obj_slice[1].start, obj_slice[1].stop
        py0, py1 = max(0, y0 - pad), min(h, y1 + pad)
        px0, px1 = max(0, x0 - pad), min(w, x1 + pad)
        local_labeled = labeled[py0:py1, px0:px1]
        local_component = local_labeled == label_id
        local_boundary = boundary_band[py0:py1, px0:px1] & local_component
        if not np.any(local_boundary):
            continue
        local_donor = colorful_high_alpha[py0:py1, px0:px1] & local_component
        if np.any(local_donor):
            donor_reach = _dilate(local_donor, pad)
        else:
            donor_reach = np.zeros_like(local_component)
        has_donor[py0:py1, px0:px1] |= local_boundary & donor_reach

    suspect_mask = boundary_band & paper_like & source_paper_like
    suspects: list[Suspect] = []
    for comp in _label_components(suspect_mask):
        area = comp["area"]
        if area < 1:
            continue
        mean_delta = float(delta_to_paper[comp["slice"]][comp["mask_local"]].mean())
        donor_fraction = float(has_donor[comp["slice"]][comp["mask_local"]].mean())
        confidence = float(
            np.clip(
                (config.paper_delta_e_paper_like - mean_delta)
                / config.paper_delta_e_paper_like,
                0.1,
                1.0,
            )
        )
        suspects.append(
            Suspect(
                kind="matte_rim",
                bbox=list(comp["bbox"]),
                area=area,
                severity=area * confidence,
                detail={
                    "mean_delta_e_to_paper": mean_delta,
                    "attached_to_colorful_donor_fraction": donor_fraction,
                },
            )
        )
    suspects.sort(key=lambda s: s.severity, reverse=True)

    ring_paper_like = edge_band & paper_like
    sweep = {
        str(t): int(np.sum(ring_paper_like & (alpha > t)))
        for t in config.matte_rim_alpha_sweep_thresholds
    }
    return suspects, sweep


# ---------------------------------------------------------------------------
# Detector 3: VANISHED-COMPONENT (deleted pale paint)
# ---------------------------------------------------------------------------


def detect_vanished_components(
    source_rgb01: np.ndarray,
    candidate_alpha_u8: np.ndarray,
    paper_field01: np.ndarray,
    config: TriageConfig,
) -> list[Suspect]:
    paper_lab = rgb_to_lab(paper_field01)
    # Anchored-OR across scales, not a strict AND: calibrating against real
    # pale/low-chroma translucent watercolor (bubbles barely above the
    # paper-like cutoff) showed a strict AND-across-all-scales threw away
    # most of a genuine bubble's evidence pixels the moment one blur radius
    # smoothed them toward paper, missing 5 of 7 known-deleted regions.  A
    # plain majority vote recovered those but let a pure paper hole get
    # falsely flagged where a nearby strong blob bled color into it under
    # blur.  Anchoring on the UNBLURRED (sigma=0) scale fixes that: a true
    # paper hole reads as paper at full resolution regardless of what a
    # blurred proxy says nearby, while a genuine faint bubble still shows
    # some real evidence unblurred; at least one blurred scale must agree
    # too, as weak corroboration against single-pixel noise.
    weak_masks = []
    for sigma in config.vanished_blur_sigmas:
        blurred = (
            source_rgb01
            if sigma <= 0
            else ndi.gaussian_filter(source_rgb01, sigma=(sigma, sigma, 0))
        )
        delta = delta_e76(rgb_to_lab(blurred), paper_lab)
        weak_masks.append(delta >= config.paper_delta_e_paper_like)
    persistent = weak_masks[0]
    if len(weak_masks) > 1:
        corroborated = np.zeros_like(weak_masks[0])
        for mask in weak_masks[1:]:
            corroborated |= mask
        persistent = persistent & corroborated

    source_delta = delta_e76(rgb_to_lab(source_rgb01), paper_lab)
    strong = source_delta >= config.paper_delta_e_strong_paint
    strong_dilated = _dilate(strong, config.vanished_attachment_radius_px)

    # The defect is a LOCAL collapse: a real painted feature can sit inside
    # one large connected non-paper region (e.g. a bubble fused onto a big
    # coral blob), so averaging alpha over the whole enclosing "persistent"
    # component would dilute a small deleted patch into a healthy mean.
    # Label the intersection with the per-pixel collapse instead.
    collapsed = candidate_alpha_u8 < config.vanished_collapse_alpha_max
    candidate_vanished = persistent & collapsed

    suspects: list[Suspect] = []
    for comp in _label_components(candidate_vanished):
        if comp["area"] < config.vanished_min_area_px:
            continue
        touches_strong = bool(
            np.any(strong_dilated[comp["slice"]] & comp["mask_local"])
        )
        if not touches_strong:
            continue
        alpha_local = candidate_alpha_u8[comp["slice"]][comp["mask_local"]]
        mean_alpha = float(alpha_local.mean())
        confidence = float(
            np.clip(1.0 - mean_alpha / config.vanished_collapse_alpha_max, 0.1, 1.0)
        )
        suspects.append(
            Suspect(
                kind="vanished_component",
                bbox=list(comp["bbox"]),
                area=comp["area"],
                severity=comp["area"] * confidence,
                detail={"mean_candidate_alpha_8bit": mean_alpha},
            )
        )
    suspects.sort(key=lambda s: s.severity, reverse=True)
    return suspects


# ---------------------------------------------------------------------------
# Detector 4: HOLE CENSUS (enclosed paper retained / wrongly opened)
# ---------------------------------------------------------------------------


def _persistence_to_suspects(
    persistence_map: np.ndarray, kind: str, min_area: int, max_persistence: int
) -> list[Suspect]:
    suspects: list[Suspect] = []
    for comp in _label_components(persistence_map > 0):
        if comp["area"] < min_area:
            continue
        local_persistence = persistence_map[comp["slice"]][comp["mask_local"]]
        persistence = int(local_persistence.max())
        confidence = float(persistence) / float(max_persistence)
        suspects.append(
            Suspect(
                kind=kind,
                bbox=list(comp["bbox"]),
                area=comp["area"],
                severity=comp["area"] * confidence,
                detail={"persistence": persistence, "max_persistence": max_persistence},
            )
        )
    suspects.sort(key=lambda s: s.severity, reverse=True)
    return suspects


def detect_hole_census(
    candidate_alpha_u8: np.ndarray,
    paperlike_source: np.ndarray,
    config: TriageConfig,
) -> Tuple[list[Suspect], list[dict[str, Any]]]:
    """Census enclosed alpha holes and opaque pockets across an alpha sweep.

    Enclosed low-alpha pockets (holes) whose SOURCE pixels are coherently
    non-paper are deleted-foreground suspects; enclosed/isolated high-alpha
    pockets whose SOURCE pixels are paper-like are retained-paper suspects.
    Persistence across the {8,32,128,224} sweep, not a single lucky cut,
    drives severity.
    """
    h, w = candidate_alpha_u8.shape
    deleted_persistence = np.zeros((h, w), dtype=np.int16)
    retained_persistence = np.zeros((h, w), dtype=np.int16)
    per_threshold: list[dict[str, Any]] = []

    thresholds = config.hole_census_alpha_thresholds
    for t in thresholds:
        bg_t = candidate_alpha_u8 <= t
        fg_t = ~bg_t
        bg_components = _label_components(bg_t)
        enclosed_bg_components = [c for c in bg_components if not c["touches_border"]]

        deleted_count = 0
        for comp in enclosed_bg_components:
            if comp["area"] < config.hole_census_min_area_px:
                continue
            local_paperlike = paperlike_source[comp["slice"]][comp["mask_local"]]
            nonpaper_fraction = 1.0 - float(local_paperlike.mean())
            if nonpaper_fraction >= config.hole_census_paperlike_fraction:
                deleted_persistence[comp["slice"]][comp["mask_local"]] += 1
                deleted_count += 1

        # Retained-paper pockets can be pixel-fused into the main opaque
        # blob (same alpha, no internal edge), so they cannot be found as
        # their own fg_t connected component.  Label the PAPER-LIKE subset
        # of fg_t directly instead: a genuinely painted object is not
        # paper-colored, so it breaks connectivity around any paper-like
        # pocket sitting inside it, regardless of how fg_t itself is fused.
        retained_candidate_mask = fg_t & paperlike_source
        retained_components = [
            c for c in _label_components(retained_candidate_mask) if not c["touches_border"]
        ]
        retained_count = 0
        for comp in retained_components:
            if comp["area"] < config.hole_census_min_area_px:
                continue
            if comp["area"] > config.hole_census_max_absolute_fg_area_px:
                continue
            retained_persistence[comp["slice"]][comp["mask_local"]] += 1
            retained_count += 1

        per_threshold.append(
            {
                "alpha_threshold": int(t),
                "enclosed_bg_components": len(enclosed_bg_components),
                "enclosed_paperlike_fg_components": len(retained_components),
                "deleted_foreground_candidates": deleted_count,
                "retained_paper_candidates": retained_count,
            }
        )

    max_persistence = len(thresholds)
    deleted_suspects = _persistence_to_suspects(
        deleted_persistence,
        "hole_census_deleted_foreground",
        config.hole_census_min_area_px,
        max_persistence,
    )
    retained_suspects = _persistence_to_suspects(
        retained_persistence,
        "hole_census_retained_paper",
        config.hole_census_min_area_px,
        max_persistence,
    )
    suspects = sorted(
        deleted_suspects + retained_suspects, key=lambda s: s.severity, reverse=True
    )
    return suspects, per_threshold


# ---------------------------------------------------------------------------
# Tile-level source-on-paper reconstruction
# ---------------------------------------------------------------------------


def compute_tile_reconstruction(
    source_rgb01: np.ndarray,
    candidate_rgb01: np.ndarray,
    candidate_alpha01: np.ndarray,
    paper_field01: np.ndarray,
    config: TriageConfig,
) -> dict[str, Any]:
    recon = candidate_rgb01 * candidate_alpha01[..., None] + paper_field01 * (
        1.0 - candidate_alpha01[..., None]
    )
    err = np.max(np.abs(recon - source_rgb01), axis=2) * 255.0
    h, w = err.shape
    tile_px = config.recon_tile_px

    rows = (h + tile_px - 1) // tile_px
    cols = (w + tile_px - 1) // tile_px
    flagged_grid = np.zeros((rows, cols), dtype=bool)
    tiles: list[dict[str, Any]] = []
    for row in range(rows):
        for col in range(cols):
            y0, y1 = row * tile_px, min((row + 1) * tile_px, h)
            x0, x1 = col * tile_px, min((col + 1) * tile_px, w)
            tile_err = err[y0:y1, x0:x1]
            p99 = float(np.percentile(tile_err, 99))
            flagged = p99 > config.recon_tile_p99_flag_8bit
            flagged_grid[row, col] = flagged
            tiles.append(
                {
                    "bbox": [int(x0), int(y0), int(x1), int(y1)],
                    "p99": p99,
                    "mean": float(tile_err.mean()),
                    "flagged": bool(flagged),
                }
            )

    labeled_regions, _ = ndi.label(flagged_grid, structure=_FULL_CONNECTIVITY)
    regions: list[dict[str, Any]] = []
    for region_id, obj_slice in enumerate(ndi.find_objects(labeled_regions), start=1):
        if obj_slice is None:
            continue
        row_slice, col_slice = obj_slice
        region_mask_local = labeled_regions[obj_slice] == region_id
        region_tiles = [
            tiles[r * cols + c]
            for r in range(row_slice.start, row_slice.stop)
            for c in range(col_slice.start, col_slice.stop)
            if labeled_regions[r, c] == region_id
        ]
        regions.append(
            {
                "bbox": [
                    int(col_slice.start * tile_px),
                    int(row_slice.start * tile_px),
                    int(min(col_slice.stop * tile_px, w)),
                    int(min(row_slice.stop * tile_px, h)),
                ],
                "tile_count": int(region_mask_local.sum()),
                "max_p99": max(t["p99"] for t in region_tiles),
            }
        )

    return {
        "tile_px": tile_px,
        "flag_p99_threshold_8bit": config.recon_tile_p99_flag_8bit,
        "global_mean_error_8bit": float(err.mean()),
        "global_p99_error_8bit": float(np.percentile(err, 99)),
        "tiles": tiles,
        "flagged_regions": regions,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


@dataclass
class TriageReport:
    paper_field: PaperField
    matte_rim_suspects: list
    matte_rim_alpha_sweep: dict
    tile_reconstruction: dict
    vanished_component_suspects: list
    hole_census_suspects: list
    hole_census_per_threshold: list
    all_suspects: list


def run_triage_arrays(
    source_rgb_u8: np.ndarray, candidate_rgba_u8: np.ndarray, config: TriageConfig
) -> TriageReport:
    """Run the full in-memory triage without mutating caller arrays."""
    config.validate()
    source = np.asarray(source_rgb_u8)
    candidate = np.asarray(candidate_rgba_u8)
    if source.ndim != 3 or source.shape[2] != 3:
        raise ValueError("source must have shape HxWx3")
    if candidate.ndim != 3 or candidate.shape[2] != 4:
        raise ValueError("candidate must have shape HxWx4")
    if candidate.shape[:2] != source.shape[:2]:
        raise ValueError(
            "candidate and source must already be the same size for analysis "
            f"(got {candidate.shape[:2]} vs {source.shape[:2]}); resample first"
        )

    source01 = source.astype(np.float32) / 255.0
    candidate_rgb01 = candidate[:, :, :3].astype(np.float32) / 255.0
    candidate_alpha_u8 = candidate[:, :, 3]
    candidate_alpha01 = candidate_alpha_u8.astype(np.float32) / 255.0

    paper_field = fit_paper_field(source01, config)
    paper_field01 = paper_field.evaluate()
    paper_field_lab = rgb_to_lab(paper_field01)
    source_lab = rgb_to_lab(source01)
    paperlike_source = delta_e76(source_lab, paper_field_lab) < config.paper_delta_e_paper_like

    matte_suspects, matte_sweep = detect_matte_rim(
        source_lab, candidate_rgb01, candidate_alpha_u8, paper_field_lab, config
    )
    tile_reconstruction = compute_tile_reconstruction(
        source01, candidate_rgb01, candidate_alpha01, paper_field01, config
    )
    vanished_suspects = detect_vanished_components(
        source01, candidate_alpha_u8, paper_field01, config
    )
    hole_suspects, hole_per_threshold = detect_hole_census(
        candidate_alpha_u8, paperlike_source, config
    )

    all_suspects = sorted(
        matte_suspects + vanished_suspects + hole_suspects,
        key=lambda s: s.severity,
        reverse=True,
    )

    return TriageReport(
        paper_field=paper_field,
        matte_rim_suspects=matte_suspects,
        matte_rim_alpha_sweep=matte_sweep,
        tile_reconstruction=tile_reconstruction,
        vanished_component_suspects=vanished_suspects,
        hole_census_suspects=hole_suspects,
        hole_census_per_threshold=hole_per_threshold,
        all_suspects=all_suspects,
    )


# ---------------------------------------------------------------------------
# Review sheet
# ---------------------------------------------------------------------------


def _composite(rgb01: np.ndarray, alpha01: np.ndarray, background_rgb01) -> np.ndarray:
    a = alpha01[..., None]
    background = np.asarray(background_rgb01, dtype=np.float32)[None, None, :]
    return np.clip(rgb01 * a + background * (1.0 - a), 0.0, 1.0)


def _boxes_overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int], margin: int = 0) -> bool:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return not (
        ax1 + margin <= bx0 or bx1 + margin <= ax0 or ay1 + margin <= by0 or by1 + margin <= ay0
    )


def _pick_clean_crops(
    suspects: Sequence[Suspect], shape_hw: Tuple[int, int], crop_px: int, count: int, seed: int
) -> list[Tuple[int, int, int, int]]:
    """Randomized, non-overlapping-with-suspects crops: blind-spot sanity check."""
    h, w = shape_hw
    if count <= 0 or h <= 0 or w <= 0:
        return []
    rng = np.random.default_rng(seed)
    suspect_boxes = [tuple(s.bbox) for s in suspects]
    picks: list[Tuple[int, int, int, int]] = []
    attempts = 0
    max_attempts = max(count * 200, 200)
    half = crop_px // 2
    while len(picks) < count and attempts < max_attempts:
        attempts += 1
        cx = int(rng.integers(0, max(w, 1)))
        cy = int(rng.integers(0, max(h, 1)))
        left = int(np.clip(cx - half, 0, max(0, w - crop_px)))
        top = int(np.clip(cy - half, 0, max(0, h - crop_px)))
        right = min(w, left + crop_px)
        bottom = min(h, top + crop_px)
        box = (left, top, right, bottom)
        if any(_boxes_overlap(box, suspect_box, margin=8) for suspect_box in suspect_boxes):
            continue
        if any(_boxes_overlap(box, picked, margin=0) for picked in picks):
            continue
        picks.append(box)
    return picks


def build_review_sheet(
    source_rgb01: np.ndarray,
    candidate_rgb01: np.ndarray,
    candidate_alpha_u8: np.ndarray,
    suspects: Sequence[Suspect],
    config: TriageConfig,
) -> Image.Image:
    h, w = candidate_alpha_u8.shape
    alpha01 = candidate_alpha_u8.astype(np.float32) / 255.0
    crop_px = max(1, min(config.review_crop_px, h, w))

    top_suspects = list(suspects[: config.review_top_n])
    clean_boxes = _pick_clean_crops(
        suspects, (h, w), crop_px, config.review_clean_crops, config.review_seed
    )

    backgrounds = (
        ("WHITE", (1.0, 1.0, 1.0)),
        ("GRAY", (0.5, 0.5, 0.5)),
        ("BLACK", (0.0, 0.0, 0.0)),
        ("MAGENTA", (1.0, 0.0, 1.0)),
    )
    row_label_h = 22
    rows: list[Tuple[str, Tuple[int, int, int, int]]] = []
    for suspect in top_suspects:
        x0, y0, x1, y1 = suspect.bbox
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        left = int(np.clip(cx - crop_px // 2, 0, max(0, w - crop_px)))
        top = int(np.clip(cy - crop_px // 2, 0, max(0, h - crop_px)))
        right = min(w, left + crop_px)
        bottom = min(h, top + crop_px)
        label = f"{suspect.kind} area={suspect.area} sev={suspect.severity:.1f} bbox={suspect.bbox}"
        rows.append((label, (left, top, right, bottom)))
    for index, box in enumerate(clean_boxes):
        rows.append((f"blind-spot-clean-{index}", box))
    if not rows:
        rows.append(("no-suspects-found", (0, 0, min(crop_px, w), min(crop_px, h))))

    board_w = crop_px * len(backgrounds)
    board_h = (crop_px + row_label_h) * len(rows)
    board = Image.new("RGB", (max(board_w, 1), max(board_h, 1)), "white")
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()

    for row_index, (label, (left, top, right, bottom)) in enumerate(rows):
        row_top = row_index * (crop_px + row_label_h)
        draw.rectangle((0, row_top, board_w - 1, row_top + row_label_h - 1), fill="white")
        draw.text((4, row_top + 4), label, fill="black", font=font)
        candidate_crop_rgb = candidate_rgb01[top:bottom, left:right]
        candidate_crop_alpha = alpha01[top:bottom, left:right]
        for col_index, (bg_label, bg_color) in enumerate(backgrounds):
            tile01 = _composite(candidate_crop_rgb, candidate_crop_alpha, bg_color)
            tile_u8 = np.clip(np.rint(tile01 * 255.0), 0, 255).astype(np.uint8)
            tile_image = Image.fromarray(tile_u8)
            if tile_image.size != (crop_px, crop_px):
                canvas = Image.new("RGB", (crop_px, crop_px), bg_label.lower())
                canvas.paste(tile_image, (0, 0))
                tile_image = canvas
            board.paste(tile_image, (col_index * crop_px, row_top + row_label_h))
    return board


# ---------------------------------------------------------------------------
# File I/O layer
# ---------------------------------------------------------------------------


def _load_source(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.mode != "RGB":
            image = image.convert("RGB")
        return np.asarray(image, dtype=np.uint8).copy()


def _load_candidate(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        return np.asarray(image, dtype=np.uint8).copy()


def resample_candidate_to_source(
    candidate_u8: np.ndarray, source_hw: Tuple[int, int]
) -> Tuple[np.ndarray, dict[str, Any]]:
    """Lanczos-downsample an integer-scale candidate (RGB and alpha) to source size."""
    sh, sw = source_hw
    ch, cw = candidate_u8.shape[:2]
    if (ch, cw) == (sh, sw):
        return candidate_u8, {"resampled": False}
    if sh <= 0 or sw <= 0 or ch % sh != 0 or cw % sw != 0 or (ch // sh) != (cw // sw):
        raise ValueError(
            f"candidate size {(cw, ch)} is not an exact integer multiple of source size {(sw, sh)}"
        )
    scale = ch // sh
    rgb_image = Image.fromarray(candidate_u8[:, :, :3]).resize((sw, sh), Image.Resampling.LANCZOS)
    alpha_image = Image.fromarray(candidate_u8[:, :, 3]).resize((sw, sh), Image.Resampling.LANCZOS)
    resized = np.dstack([np.asarray(rgb_image), np.asarray(alpha_image)]).astype(np.uint8)
    return resized, {"resampled": True, "scale": int(scale), "original_size_wh": [int(cw), int(ch)]}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def process_files(
    source_path: Path,
    candidate_path: Path,
    report_path: Path,
    review_sheet_path: Optional[Path],
    config: TriageConfig,
) -> dict[str, Any]:
    source_u8 = _load_source(source_path)
    candidate_raw_u8 = _load_candidate(candidate_path)
    candidate_u8, resample_info = resample_candidate_to_source(
        candidate_raw_u8, source_u8.shape[:2]
    )

    report = run_triage_arrays(source_u8, candidate_u8, config)

    payload: dict[str, Any] = {
        "schema": "batch-triage/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "source": {
                "path": str(source_path),
                "size_wh": [int(source_u8.shape[1]), int(source_u8.shape[0])],
            },
            "candidate": {
                "path": str(candidate_path),
                "size_wh": [int(candidate_raw_u8.shape[1]), int(candidate_raw_u8.shape[0])],
            },
            "resample": resample_info,
        },
        "paper_field": asdict(report.paper_field),
        "matte_rim": {
            "suspects": [asdict(s) for s in report.matte_rim_suspects],
            "alpha_threshold_sweep": report.matte_rim_alpha_sweep,
        },
        "tile_reconstruction": report.tile_reconstruction,
        "vanished_component": {
            "suspects": [asdict(s) for s in report.vanished_component_suspects],
        },
        "hole_census": {
            "suspects": [asdict(s) for s in report.hole_census_suspects],
            "per_threshold": report.hole_census_per_threshold,
        },
        "summary": {
            "matte_rim_count": len(report.matte_rim_suspects),
            "vanished_component_count": len(report.vanished_component_suspects),
            "hole_census_count": len(report.hole_census_suspects),
            "total_suspects": len(report.all_suspects),
        },
    }
    payload = _json_safe(payload)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if review_sheet_path is not None:
        source01 = source_u8.astype(np.float32) / 255.0
        candidate_rgb01 = candidate_u8[:, :, :3].astype(np.float32) / 255.0
        review_sheet_path.parent.mkdir(parents=True, exist_ok=True)
        build_review_sheet(
            source01, candidate_rgb01, candidate_u8[:, :, 3], report.all_suspects, config
        ).save(review_sheet_path)
        payload["review_sheet_path"] = str(review_sheet_path)

    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="source RGB PNG")
    parser.add_argument("--candidate", type=Path, required=True, help="candidate straight-RGBA PNG")
    parser.add_argument("--report", type=Path, required=True, help="output JSON report path")
    parser.add_argument("--review-sheet", type=Path, help="output review-sheet PNG path")
    parser.add_argument("--top-n", type=int, default=12, help="max suspects on the review sheet")
    parser.add_argument("--clean-crops", type=int, default=3, help="randomized blind-spot crops")
    parser.add_argument("--crop-px", type=int, default=160, help="native 1:1 crop side, pixels")
    parser.add_argument("--seed", type=int, default=0, help="seed for randomized clean crops")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    config = TriageConfig(
        review_top_n=args.top_n,
        review_clean_crops=args.clean_crops,
        review_crop_px=args.crop_px,
        review_seed=args.seed,
    )
    try:
        payload = process_files(
            args.source.expanduser().resolve(),
            args.candidate.expanduser().resolve(),
            args.report.expanduser().resolve(),
            args.review_sheet.expanduser().resolve() if args.review_sheet else None,
            config,
        )
    except OSError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(payload.get("summary", {}), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
