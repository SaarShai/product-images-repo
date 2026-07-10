#!/usr/bin/env python3
"""Native-resolution, correction-led background removal.

This module deliberately separates four concerns:

1. a proposal alpha becomes a conservative trimap;
2. sparse human sure-FG/sure-BG corrections override that trimap;
3. an explicitly selected matting backend solves soft alpha;
4. foreground RGB is recovered independently from alpha.

The command writes candidates only.  It refuses paths inside ``final`` or
``finals`` folders so production promotion remains a separate, reviewed step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi


Image.MAX_IMAGE_PIXELS = None

VITMATTE_MODEL = "hustvl/vitmatte-small-composition-1k"
VITMATTE_REVISION = "6a58ad7646403c1df626fbd746900aec7361ea1d"
FINAL_PATH_PARTS = {"final", "finals"}

DECONTAM_BOUNDARY_WIDTH_PX = 2
DECONTAM_TARGET_RADIUS_PX = 8
DECONTAM_INTERIOR_ALPHA = 0.98
DECONTAM_FOREGROUND_ALPHA = 16.0 / 255.0
DECONTAM_MINIMUM_NEW_ALPHA = 17.0 / 255.0
DECONTAM_PAPER_DISTANCE_8BIT = 80.0
DECONTAM_MAX_RECOMPOSITION_ERROR_8BIT = 8.0

AlphaSolver = Callable[[np.ndarray, np.ndarray], np.ndarray]
ForegroundEstimator = Callable[[np.ndarray, np.ndarray], np.ndarray]


@dataclass(frozen=True)
class PipelineConfig:
    proposal_fg_threshold: float = 0.95
    proposal_bg_threshold: float = 0.05
    inner_distance_px: int = 3
    outer_distance_px: int = 3
    correction_unlock_radius_px: int = 6
    correction_primary_min: int = 200
    correction_other_max: int = 64
    binary: bool = False
    binary_threshold: float = 0.5
    residual_alpha_floor: float = 0.20
    residual_max_adjustment: float = 0.35
    edge_decontamination: bool = True
    decontam_paper_distance_8bit: float = DECONTAM_PAPER_DISTANCE_8BIT
    closed_form_maxiter: int = 1000
    vitmatte_model: str = VITMATTE_MODEL
    vitmatte_revision: str = VITMATTE_REVISION
    device: str = "auto"

    def validate(self) -> None:
        if not 0.0 <= self.proposal_bg_threshold < self.proposal_fg_threshold <= 1.0:
            raise ValueError("proposal thresholds must satisfy 0 <= BG < FG <= 1")
        if self.inner_distance_px < 0 or self.outer_distance_px < 0:
            raise ValueError("trimap distances must be non-negative")
        if self.correction_unlock_radius_px < 0:
            raise ValueError("correction unlock radius must be non-negative")
        if not 0 <= self.correction_other_max < self.correction_primary_min <= 255:
            raise ValueError("correction color thresholds are invalid")
        if not 0.0 <= self.binary_threshold <= 1.0:
            raise ValueError("binary threshold must be in [0, 1]")
        if not 0.0 < self.residual_alpha_floor <= 1.0:
            raise ValueError("residual alpha floor must be in (0, 1]")
        if not 0.0 <= self.residual_max_adjustment <= 1.0:
            raise ValueError("residual max adjustment must be in [0, 1]")
        if self.closed_form_maxiter <= 0:
            raise ValueError("closed-form max iterations must be positive")
        if self.decontam_paper_distance_8bit <= 0.0:
            raise ValueError("decontam paper distance must be positive")
        if self.device not in {"auto", "mps", "cpu"}:
            raise ValueError("device must be auto, mps, or cpu")


@dataclass
class PipelineResult:
    foreground_rgb: np.ndarray
    alpha: np.ndarray
    trimap: np.ndarray
    correction_fg: np.ndarray
    correction_bg: np.ndarray
    background_rgb: np.ndarray
    backend: dict[str, Any]
    metrics: dict[str, Any]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_source_rgb(source: np.ndarray) -> np.ndarray:
    array = np.asarray(source)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError("source must have shape HxWx3")
    if not np.all(np.isfinite(array)):
        raise ValueError("source contains non-finite values")
    if np.issubdtype(array.dtype, np.integer):
        if array.min() < 0 or array.max() > 255:
            raise ValueError("integer source values must be in [0, 255]")
        result = array.astype(np.float32) / 255.0
    else:
        result = array.astype(np.float32, copy=True)
        if result.min() < 0.0 or result.max() > 1.0:
            raise ValueError("floating source values must be in [0, 1]")
    return np.ascontiguousarray(result.copy())


def _as_alpha(proposal: np.ndarray, shape_hw: Tuple[int, int]) -> np.ndarray:
    array = np.asarray(proposal)
    if array.shape != shape_hw:
        raise ValueError(
            "proposal dimensions must exactly match source: "
            f"expected {shape_hw[::-1]} WH, got {array.shape[::-1]} WH"
        )
    if not np.all(np.isfinite(array)):
        raise ValueError("proposal contains non-finite values")
    if np.issubdtype(array.dtype, np.integer):
        if array.min() < 0 or array.max() > 255:
            raise ValueError("integer proposal values must be in [0, 255]")
        result = array.astype(np.float32) / 255.0
    else:
        result = array.astype(np.float32, copy=True)
        if result.min() < 0.0 or result.max() > 1.0:
            raise ValueError("floating proposal values must be in [0, 1]")
    return np.ascontiguousarray(result.copy())


def _disk(radius: int) -> np.ndarray:
    if radius <= 0:
        return np.ones((1, 1), dtype=bool)
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return (xx * xx + yy * yy) <= radius * radius


def _erode(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius == 0:
        return mask.copy()
    return ndi.binary_erosion(mask, structure=_disk(radius), border_value=0)


def build_proposal_trimap(proposal: np.ndarray, config: PipelineConfig) -> np.ndarray:
    """Convert proposal alpha to a conservative 0/0.5/1 trimap."""
    config.validate()
    alpha = np.asarray(proposal, dtype=np.float32)
    if alpha.ndim != 2 or not np.all(np.isfinite(alpha)):
        raise ValueError("proposal alpha must be a finite HxW array")
    if alpha.min() < 0.0 or alpha.max() > 1.0:
        raise ValueError("proposal alpha must be in [0, 1]")

    sure_fg = _erode(alpha >= config.proposal_fg_threshold, config.inner_distance_px)
    sure_bg = _erode(alpha <= config.proposal_bg_threshold, config.outer_distance_px)
    if np.any(sure_fg & sure_bg):
        raise ValueError("proposal produced overlapping sure-FG and sure-BG")

    trimap = np.full(alpha.shape, 0.5, dtype=np.float32)
    trimap[sure_bg] = 0.0
    trimap[sure_fg] = 1.0
    return trimap


def validate_correction_masks(foreground: np.ndarray, background: np.ndarray) -> None:
    if foreground.shape != background.shape or foreground.ndim != 2:
        raise ValueError("correction masks must be same-size HxW arrays")
    if np.any(np.asarray(foreground, dtype=bool) & np.asarray(background, dtype=bool)):
        raise ValueError("sure-FG and sure-BG corrections overlap")


def decode_correction_overlay(
    overlay_rgba: np.ndarray,
    shape_hw: Tuple[int, int],
    config: PipelineConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """Decode opaque red/blue strokes; alpha zero is strictly unknown.

    A fully opaque overlay is rejected as flattened.  Partially transparent,
    weak, and ambiguous painted pixels are also rejected instead of guessed.
    """
    config.validate()
    overlay = np.asarray(overlay_rgba)
    expected = (shape_hw[0], shape_hw[1], 4)
    if overlay.shape != expected:
        raise ValueError(
            "correction overlay dimensions must exactly match source: "
            f"expected {expected}, got {overlay.shape}"
        )
    if overlay.dtype != np.uint8:
        raise ValueError("correction overlay must be 8-bit RGBA")

    alpha = overlay[:, :, 3]
    if np.all(alpha > 0):
        raise ValueError(
            "correction overlay is fully opaque/flattened; unknown pixels must have alpha=0"
        )
    painted = alpha > 0
    if np.any(painted & (alpha != 255)):
        raise ValueError("painted correction pixels must be fully opaque (alpha=255)")

    red = overlay[:, :, 0]
    green = overlay[:, :, 1]
    blue = overlay[:, :, 2]
    red_primary = painted & (red >= config.correction_primary_min) & (
        green <= config.correction_other_max
    )
    blue_primary = painted & (blue >= config.correction_primary_min) & (
        green <= config.correction_other_max
    )
    if np.any(red_primary & blue_primary):
        raise ValueError("ambiguous correction pixels match both red FG and blue BG")

    sure_fg = red_primary & (blue <= config.correction_other_max)
    sure_bg = blue_primary & (red <= config.correction_other_max)
    unclassified = painted & ~(sure_fg | sure_bg)
    if np.any(unclassified):
        count = int(unclassified.sum())
        raise ValueError(f"{count} painted correction pixels have weak/ambiguous colors")
    validate_correction_masks(sure_fg, sure_bg)
    return sure_fg, sure_bg


def apply_corrections_to_trimap(
    trimap: np.ndarray,
    sure_fg: np.ndarray,
    sure_bg: np.ndarray,
    unlock_radius_px: int,
) -> np.ndarray:
    """Unlock around sparse strokes, then apply their exact labels last."""
    result = np.asarray(trimap, dtype=np.float32).copy()
    if result.ndim != 2:
        raise ValueError("trimap must be HxW")
    fg = np.asarray(sure_fg, dtype=bool)
    bg = np.asarray(sure_bg, dtype=bool)
    if fg.shape != result.shape or bg.shape != result.shape:
        raise ValueError("correction masks must match trimap dimensions")
    validate_correction_masks(fg, bg)
    if unlock_radius_px < 0:
        raise ValueError("correction unlock radius must be non-negative")

    marks = fg | bg
    if unlock_radius_px > 0 and np.any(marks):
        # A dense 221x221 structuring element (the real image-14 correction
        # radius) is needlessly memory-heavy.  Euclidean distance is exactly
        # the same circular unlock rule and stays O(image pixels).
        unlocked = ndi.distance_transform_edt(~marks) <= unlock_radius_px
        result[unlocked] = 0.5
    result[bg] = 0.0
    result[fg] = 1.0
    return result


def validate_trimap(trimap: np.ndarray) -> None:
    values = np.asarray(trimap)
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ValueError("trimap must be a finite HxW array")
    if not np.any(values == 0.0):
        raise ValueError("trimap has no sure-BG labels")
    if not np.any(values == 1.0):
        raise ValueError("trimap has no sure-FG labels")
    if np.any(~np.isin(values, (0.0, 0.5, 1.0))):
        raise ValueError("trimap values must be exactly 0, 0.5, or 1")


def _solve_closed_form(
    source_rgb: np.ndarray, trimap: np.ndarray, config: PipelineConfig
) -> Tuple[np.ndarray, dict[str, Any]]:
    from pymatting import estimate_alpha_cf

    started = time.perf_counter()
    alpha = estimate_alpha_cf(
        source_rgb.astype(np.float64),
        trimap.astype(np.float64),
        cg_kwargs={"maxiter": config.closed_form_maxiter},
    )
    return np.asarray(alpha, dtype=np.float32), {
        "backend_used": "closed_form",
        "seconds": time.perf_counter() - started,
        "maxiter": config.closed_form_maxiter,
    }


def _solve_vitmatte(
    source_rgb: np.ndarray, trimap: np.ndarray, config: PipelineConfig
) -> Tuple[np.ndarray, dict[str, Any]]:
    import torch
    from transformers import VitMatteForImageMatting, VitMatteImageProcessor

    requested_device = config.device
    if requested_device == "auto":
        device_name = "mps" if torch.backends.mps.is_available() else "cpu"
    else:
        device_name = requested_device
    if device_name == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS was requested but is unavailable")
    device = torch.device(device_name)

    started = time.perf_counter()
    processor = VitMatteImageProcessor.from_pretrained(
        config.vitmatte_model,
        revision=config.vitmatte_revision,
        local_files_only=True,
    )
    model = VitMatteForImageMatting.from_pretrained(
        config.vitmatte_model,
        revision=config.vitmatte_revision,
        local_files_only=True,
    ).eval()
    model.to(device)

    rgb8 = np.clip(np.rint(source_rgb * 255.0), 0, 255).astype(np.uint8)
    trimap8 = np.where(trimap == 0.0, 0, np.where(trimap == 1.0, 255, 128)).astype(
        np.uint8
    )
    inputs = processor(
        images=Image.fromarray(rgb8),
        trimaps=Image.fromarray(trimap8),
        return_tensors="pt",
    )
    pixel_values = inputs["pixel_values"].to(device)
    with torch.inference_mode():
        output = model(pixel_values=pixel_values).alphas
    if device.type == "mps":
        torch.mps.synchronize()

    height, width = source_rgb.shape[:2]
    if output.shape[-2] < height or output.shape[-1] < width:
        raise RuntimeError(
            f"ViTMatte output {tuple(output.shape[-2:])} is smaller than source {(height, width)}"
        )
    alpha = output[0, 0, :height, :width].detach().float().cpu().numpy()
    return np.asarray(alpha, dtype=np.float32), {
        "backend_used": "vitmatte",
        "model": config.vitmatte_model,
        "revision": config.vitmatte_revision,
        "device_requested": requested_device,
        "device_used": device.type,
        "processor_shape": list(pixel_values.shape),
        "seconds": time.perf_counter() - started,
    }


def solve_alpha(
    source_rgb: np.ndarray,
    trimap: np.ndarray,
    backend: str,
    config: PipelineConfig,
    allow_fallback: bool = False,
    solver: Optional[AlphaSolver] = None,
) -> Tuple[np.ndarray, dict[str, Any]]:
    """Solve alpha without ever silently changing backend."""
    validate_trimap(trimap)
    if backend not in {"vitmatte", "closed_form"}:
        raise ValueError("backend must be vitmatte or closed_form")
    if solver is not None:
        alpha = np.asarray(solver(source_rgb.copy(), trimap.copy()), dtype=np.float32)
        info = {"backend_requested": backend, "backend_used": "injected-test-solver"}
    else:
        try:
            if backend == "vitmatte":
                alpha, info = _solve_vitmatte(source_rgb, trimap, config)
            else:
                alpha, info = _solve_closed_form(source_rgb, trimap, config)
            info["backend_requested"] = backend
        except Exception as error:
            if not (allow_fallback and backend == "vitmatte"):
                raise
            alpha, info = _solve_closed_form(source_rgb, trimap, config)
            info.update(
                backend_requested="vitmatte",
                fallback_allowed=True,
                fallback_error=f"{type(error).__name__}: {error}",
            )

    if alpha.shape != trimap.shape:
        raise ValueError(
            f"solver alpha shape {alpha.shape} does not match trimap {trimap.shape}"
        )
    if not np.all(np.isfinite(alpha)):
        raise ValueError("solver returned non-finite alpha")
    return np.clip(alpha, 0.0, 1.0).astype(np.float32), info


def clamp_alpha(
    alpha: np.ndarray,
    trimap: np.ndarray,
    correction_fg: np.ndarray,
    correction_bg: np.ndarray,
    config: PipelineConfig,
) -> np.ndarray:
    """Clamp all sure labels, with human corrections applied last again."""
    result = np.asarray(alpha, dtype=np.float32).copy()
    if config.binary:
        result = (result >= config.binary_threshold).astype(np.float32)
    result[trimap == 0.0] = 0.0
    result[trimap == 1.0] = 1.0
    result[correction_bg] = 0.0
    result[correction_fg] = 1.0
    if not np.all(np.isfinite(result)):
        raise ValueError("alpha became non-finite during clamping")
    return np.clip(result, 0.0, 1.0)


def estimate_background_rgb(source_rgb: np.ndarray, trimap: np.ndarray) -> np.ndarray:
    sure_bg = trimap == 0.0
    if np.any(sure_bg):
        samples = source_rgb[sure_bg]
    else:
        samples = np.concatenate(
            (
                source_rgb[0, :, :],
                source_rgb[-1, :, :],
                source_rgb[:, 0, :],
                source_rgb[:, -1, :],
            ),
            axis=0,
        )
    value = np.median(samples, axis=0).astype(np.float32)
    if value.shape != (3,) or not np.all(np.isfinite(value)):
        raise ValueError("could not estimate a finite paper/background color")
    return np.clip(value, 0.0, 1.0)


def apply_residual_correction(
    source_rgb: np.ndarray,
    foreground_rgb: np.ndarray,
    alpha: np.ndarray,
    background_rgb: np.ndarray,
    alpha_floor: float,
    max_adjustment: float,
) -> Tuple[np.ndarray, dict[str, Any]]:
    """Bounded algebraic correction above a safe alpha floor.

    The division by alpha is never evaluated below ``alpha_floor``.  This
    improves source-on-paper recomposition without amplifying low-alpha noise.
    """
    source = _as_source_rgb(source_rgb)
    foreground = np.asarray(foreground_rgb, dtype=np.float32)
    a = np.asarray(alpha, dtype=np.float32)
    background = np.asarray(background_rgb, dtype=np.float32)
    if foreground.shape != source.shape or a.shape != source.shape[:2]:
        raise ValueError("foreground/alpha dimensions must match source")
    if background.shape != (3,) or not np.all(np.isfinite(background)):
        raise ValueError("background RGB must be a finite length-3 vector")
    if not 0.0 < alpha_floor <= 1.0:
        raise ValueError("alpha floor must be in (0, 1]")
    if not 0.0 <= max_adjustment <= 1.0:
        raise ValueError("max adjustment must be in [0, 1]")

    # A third-party estimator can be imperfect at alpha extremes.  Sanitize it
    # before arithmetic and keep every output channel bounded.
    foreground = np.nan_to_num(foreground, nan=0.0, posinf=1.0, neginf=0.0)
    foreground = np.clip(foreground, 0.0, 1.0)
    a = np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0)
    a = np.clip(a, 0.0, 1.0)
    background = np.clip(background, 0.0, 1.0)
    a3 = a[:, :, None]
    background3 = background[None, None, :]
    before_recomposition = a3 * foreground + (1.0 - a3) * background3
    eligible = a >= alpha_floor

    corrected = foreground.copy()
    if np.any(eligible) and max_adjustment > 0.0:
        residual = source - before_recomposition
        denominator = a3[eligible]
        delta = residual[eligible] / denominator
        delta = np.clip(delta, -max_adjustment, max_adjustment)
        corrected[eligible] = np.clip(foreground[eligible] + delta, 0.0, 1.0)
    after_recomposition = a3 * corrected + (1.0 - a3) * background3

    if np.any(eligible):
        before_error = np.abs(source[eligible] - before_recomposition[eligible])
        after_error = np.abs(source[eligible] - after_recomposition[eligible])
        before_mae = float(before_error.mean())
        after_mae = float(after_error.mean())
        before_p95 = float(np.percentile(before_error, 95))
        after_p95 = float(np.percentile(after_error, 95))
    else:
        before_mae = after_mae = before_p95 = after_p95 = 0.0
    metrics = {
        "alpha_floor": alpha_floor,
        "max_adjustment": max_adjustment,
        "eligible_pixels": int(eligible.sum()),
        "eligible_recomposition_mae_before": before_mae,
        "eligible_recomposition_mae_after": after_mae,
        "eligible_recomposition_p95_before": before_p95,
        "eligible_recomposition_p95_after": after_p95,
    }
    if not np.all(np.isfinite(corrected)):
        raise ValueError("foreground recovery produced non-finite RGB")
    return np.clip(corrected, 0.0, 1.0).astype(np.float32), metrics


def decontaminate_boundary_rgb(
    source_rgb: np.ndarray,
    foreground_rgb: np.ndarray,
    alpha: np.ndarray,
    background_rgb: np.ndarray,
    protected_mask: Optional[np.ndarray] = None,
    boundary_width_px: int = DECONTAM_BOUNDARY_WIDTH_PX,
    target_radius_px: int = DECONTAM_TARGET_RADIUS_PX,
    interior_alpha: float = DECONTAM_INTERIOR_ALPHA,
    foreground_alpha: float = DECONTAM_FOREGROUND_ALPHA,
    minimum_new_alpha: float = DECONTAM_MINIMUM_NEW_ALPHA,
    paper_distance_8bit: float = DECONTAM_PAPER_DISTANCE_8BIT,
    max_recomposition_error_8bit: float = DECONTAM_MAX_RECOMPOSITION_ERROR_8BIT,
) -> Tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Jointly replace paper-colored boundary RGB and re-solve its alpha.

    A low-alpha pixel has infinitely many valid foreground/alpha pairs.  This
    stage selects a nearby, colorful, high-alpha foreground color from the same
    connected component, then solves the least-squares alpha that reconstructs
    the original source over its paper color.  Pixels are changed only when the
    reconstructed source remains within a bounded per-channel error.

    This is deliberately a joint RGB/alpha operation.  Recoloring straight RGB
    alone creates a dark rim; reducing alpha alone deletes pale watercolor.
    """
    source = _as_source_rgb(source_rgb)
    foreground = np.asarray(foreground_rgb, dtype=np.float32)
    a = np.asarray(alpha, dtype=np.float32)
    paper = np.asarray(background_rgb, dtype=np.float32)
    if foreground.shape != source.shape or a.shape != source.shape[:2]:
        raise ValueError("foreground/alpha dimensions must match source")
    if paper.shape != (3,) or not np.all(np.isfinite(paper)):
        raise ValueError("background RGB must be a finite length-3 vector")
    if boundary_width_px <= 0 or target_radius_px <= 0:
        raise ValueError("decontamination widths must be positive")
    if not 0.0 < interior_alpha <= 1.0:
        raise ValueError("decontamination interior alpha must be in (0, 1]")
    if not 0.0 <= foreground_alpha < minimum_new_alpha <= 1.0:
        raise ValueError("decontamination alpha thresholds are invalid")
    if paper_distance_8bit <= 0.0 or max_recomposition_error_8bit < 0.0:
        raise ValueError("decontamination color/error thresholds are invalid")

    foreground = np.clip(
        np.nan_to_num(foreground, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0
    )
    a = np.clip(np.nan_to_num(a, nan=0.0, posinf=1.0, neginf=0.0), 0.0, 1.0)
    paper = np.clip(paper, 0.0, 1.0)
    if protected_mask is None:
        protected = np.zeros(a.shape, dtype=bool)
    else:
        protected = np.asarray(protected_mask, dtype=bool)
        if protected.shape != a.shape:
            raise ValueError("decontamination protected mask must match alpha")

    foreground_support = a > foreground_alpha
    square = np.ones((3, 3), dtype=bool)
    boundary = foreground_support & ndi.binary_dilation(
        ~foreground_support,
        structure=square,
        iterations=boundary_width_px,
    )
    interior = ndi.binary_erosion(a >= interior_alpha, iterations=2)
    if not np.any(boundary) or not np.any(interior):
        return foreground.copy(), a.copy(), {
            "enabled": True,
            "changed_pixels": 0,
            "skipped_reason": "no eligible boundary or high-alpha interior",
        }

    component_labels, _ = ndi.label(foreground_support, structure=square)
    distance, indices = ndi.distance_transform_edt(
        ~interior, return_indices=True
    )
    target = foreground[indices[0], indices[1]]
    same_component = (component_labels != 0) & (
        component_labels == component_labels[indices[0], indices[1]]
    )

    current_paper_distance = np.linalg.norm(
        (foreground - paper[None, None, :]) * 255.0, axis=2
    )
    target_paper_distance = np.linalg.norm(
        (target - paper[None, None, :]) * 255.0, axis=2
    )
    background_minus_target = paper[None, None, :] - target
    background_minus_source = paper[None, None, :] - source
    denominator = np.sum(background_minus_target * background_minus_target, axis=2)
    solved_alpha = np.divide(
        np.sum(background_minus_target * background_minus_source, axis=2),
        denominator,
        out=np.zeros_like(a),
        where=denominator > 1e-8,
    )
    solved_alpha = np.clip(solved_alpha, 0.0, 1.0)
    recomposed = (
        solved_alpha[:, :, None] * target
        + (1.0 - solved_alpha[:, :, None]) * paper[None, None, :]
    )
    reconstruction_error = np.max(np.abs(recomposed - source) * 255.0, axis=2)

    changed = (
        boundary
        & ~protected
        & same_component
        & (distance <= target_radius_px)
        & (current_paper_distance < paper_distance_8bit)
        & (target_paper_distance >= paper_distance_8bit)
        & (solved_alpha >= minimum_new_alpha)
        & (reconstruction_error <= max_recomposition_error_8bit)
    )
    result_foreground = foreground.copy()
    result_alpha = a.copy()
    result_foreground[changed] = target[changed]
    result_alpha[changed] = solved_alpha[changed]

    if np.any(changed):
        changed_error = reconstruction_error[changed]
        error_max = float(changed_error.max())
        error_p95 = float(np.percentile(changed_error, 95))
    else:
        error_max = error_p95 = 0.0
    metrics = {
        "enabled": True,
        "method": "same-component-color-plus-least-squares-alpha",
        "changed_pixels": int(changed.sum()),
        "boundary_pixels": int(boundary.sum()),
        "protected_pixels": int(protected.sum()),
        "boundary_width_px": boundary_width_px,
        "target_radius_px": target_radius_px,
        "interior_alpha": interior_alpha,
        "foreground_alpha": foreground_alpha,
        "minimum_new_alpha": minimum_new_alpha,
        "paper_distance_8bit": paper_distance_8bit,
        "max_recomposition_error_8bit": max_recomposition_error_8bit,
        "changed_recomposition_error_max_8bit": error_max,
        "changed_recomposition_error_p95_8bit": error_p95,
    }
    return (
        np.clip(result_foreground, 0.0, 1.0).astype(np.float32),
        np.clip(result_alpha, 0.0, 1.0).astype(np.float32),
        metrics,
    )


def _default_foreground_estimator(image: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    from pymatting import estimate_foreground_ml

    return np.asarray(estimate_foreground_ml(image, alpha), dtype=np.float32)


def recover_foreground_rgb(
    source_rgb: np.ndarray,
    alpha: np.ndarray,
    trimap: np.ndarray,
    config: PipelineConfig,
    foreground_estimator: Optional[ForegroundEstimator] = None,
    background_rgb: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    estimator = foreground_estimator or _default_foreground_estimator
    foreground = np.asarray(estimator(source_rgb.copy(), alpha.copy()), dtype=np.float32)
    if foreground.shape != source_rgb.shape:
        raise ValueError("foreground estimator returned the wrong dimensions")
    paper = (
        estimate_background_rgb(source_rgb, trimap)
        if background_rgb is None
        else np.asarray(background_rgb, dtype=np.float32)
    )
    corrected, metrics = apply_residual_correction(
        source_rgb,
        foreground,
        alpha,
        paper,
        config.residual_alpha_floor,
        config.residual_max_adjustment,
    )
    return corrected, np.clip(paper, 0.0, 1.0), metrics


def alpha_summary(alpha: np.ndarray) -> dict[str, Any]:
    values = np.asarray(alpha, dtype=np.float32)
    return {
        "min": float(values.min()),
        "max": float(values.max()),
        "mean": float(values.mean()),
        "exact_zero_pixels": int(np.sum(values == 0.0)),
        "exact_one_pixels": int(np.sum(values == 1.0)),
        "soft_pixels": int(np.sum((values > 0.0) & (values < 1.0))),
        "percentiles": {
            str(percentile): float(np.percentile(values, percentile))
            for percentile in (0, 1, 5, 50, 95, 99, 100)
        },
    }


def run_pipeline_arrays(
    source_rgb: np.ndarray,
    proposal_alpha: np.ndarray,
    correction_overlay: Optional[np.ndarray],
    backend: str,
    config: PipelineConfig,
    allow_fallback: bool = False,
    solver: Optional[AlphaSolver] = None,
    foreground_estimator: Optional[ForegroundEstimator] = None,
    background_rgb: Optional[np.ndarray] = None,
) -> PipelineResult:
    """Run the full in-memory pipeline without mutating caller arrays."""
    config.validate()
    source = _as_source_rgb(source_rgb)
    proposal = _as_alpha(proposal_alpha, source.shape[:2])
    proposal_trimap = build_proposal_trimap(proposal, config)

    if correction_overlay is None:
        correction_fg = np.zeros(source.shape[:2], dtype=bool)
        correction_bg = np.zeros(source.shape[:2], dtype=bool)
    else:
        correction_fg, correction_bg = decode_correction_overlay(
            np.asarray(correction_overlay), source.shape[:2], config
        )
    trimap = apply_corrections_to_trimap(
        proposal_trimap,
        correction_fg,
        correction_bg,
        config.correction_unlock_radius_px,
    )

    solved_alpha, backend_info = solve_alpha(
        source,
        trimap,
        backend,
        config,
        allow_fallback=allow_fallback,
        solver=solver,
    )
    alpha = clamp_alpha(solved_alpha, trimap, correction_fg, correction_bg, config)
    foreground, paper, residual_metrics = recover_foreground_rgb(
        source,
        alpha,
        trimap,
        config,
        foreground_estimator=foreground_estimator,
        background_rgb=background_rgb,
    )
    if config.edge_decontamination and not config.binary:
        foreground, alpha, decontamination_metrics = decontaminate_boundary_rgb(
            source,
            foreground,
            alpha,
            paper,
            protected_mask=trimap != 0.5,
            paper_distance_8bit=config.decontam_paper_distance_8bit,
        )
    else:
        decontamination_metrics = {
            "enabled": False,
            "changed_pixels": 0,
            "skipped_reason": (
                "binary alpha requested"
                if config.binary
                else "disabled by configuration"
            ),
        }
    metrics = {
        "source_size_wh": [int(source.shape[1]), int(source.shape[0])],
        "native_resolution_preserved": True,
        "proposal": {
            "sure_fg_pixels_before_corrections": int(
                np.sum(proposal_trimap == 1.0)
            ),
            "sure_bg_pixels_before_corrections": int(
                np.sum(proposal_trimap == 0.0)
            ),
        },
        "corrections": {
            "sure_fg_pixels": int(correction_fg.sum()),
            "sure_bg_pixels": int(correction_bg.sum()),
            "unlock_radius_px": config.correction_unlock_radius_px,
            "labels_clamped_after_solver": True,
        },
        "trimap": {
            "sure_bg_pixels": int(np.sum(trimap == 0.0)),
            "unknown_pixels": int(np.sum(trimap == 0.5)),
            "sure_fg_pixels": int(np.sum(trimap == 1.0)),
        },
        "alpha": alpha_summary(alpha),
        "alpha_mode": "binary-explicit" if config.binary else "soft-straight-default",
        "foreground_rgb": {
            "representation": "straight/unassociated",
            "background_rgb_0_1": [float(value) for value in paper],
            "residual_correction": residual_metrics,
            "edge_decontamination": decontamination_metrics,
        },
    }
    return PipelineResult(
        foreground_rgb=foreground,
        alpha=alpha,
        trimap=trimap,
        correction_fg=correction_fg,
        correction_bg=correction_bg,
        background_rgb=paper,
        backend=backend_info,
        metrics=metrics,
    )


def composite(
    foreground_rgb: np.ndarray, alpha: np.ndarray, background_rgb: Sequence[float]
) -> np.ndarray:
    foreground = np.asarray(foreground_rgb, dtype=np.float32)
    a = np.asarray(alpha, dtype=np.float32)[:, :, None]
    background = np.asarray(background_rgb, dtype=np.float32)[None, None, :]
    result = foreground * a + background * (1.0 - a)
    return np.clip(result, 0.0, 1.0)


def make_review_board(
    foreground_rgb: np.ndarray,
    alpha: np.ndarray,
    max_tile_side: int = 1200,
) -> Image.Image:
    if max_tile_side <= 0:
        raise ValueError("review max tile side must be positive")
    backgrounds = (
        ("WHITE", (1.0, 1.0, 1.0)),
        ("GRAY", (0.5, 0.5, 0.5)),
        ("BLACK", (0.0, 0.0, 0.0)),
        ("MAGENTA", (1.0, 0.0, 1.0)),
    )
    height, width = alpha.shape
    scale = min(1.0, max_tile_side / float(max(height, width)))
    tile_width = max(1, int(round(width * scale)))
    tile_height = max(1, int(round(height * scale)))
    label_height = 28
    board = Image.new("RGB", (tile_width * 2, (tile_height + label_height) * 2), "white")
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    for index, (label, background) in enumerate(backgrounds):
        row, column = divmod(index, 2)
        tile = np.clip(
            np.rint(composite(foreground_rgb, alpha, background) * 255.0), 0, 255
        ).astype(np.uint8)
        image = Image.fromarray(tile)
        if image.size != (tile_width, tile_height):
            image = image.resize((tile_width, tile_height), Image.Resampling.LANCZOS)
        x = column * tile_width
        y = row * (tile_height + label_height)
        draw.rectangle((x, y, x + tile_width - 1, y + label_height - 1), fill="white")
        draw.text((x + 6, y + 8), label, fill="black", font=font)
        board.paste(image, (x, y + label_height))
    return board


def save_straight_rgba(path: Path, foreground_rgb: np.ndarray, alpha: np.ndarray) -> None:
    rgb8 = np.clip(np.rint(foreground_rgb * 255.0), 0, 255).astype(np.uint8)
    alpha8 = np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8)
    Image.fromarray(np.dstack((rgb8, alpha8))).save(path)


def reject_final_path(path: Path) -> None:
    resolved_parts = {part.casefold() for part in path.expanduser().resolve().parts}
    forbidden = resolved_parts & FINAL_PATH_PARTS
    if forbidden:
        raise ValueError(
            f"candidate core refuses final-path promotion ({sorted(forbidden)}): {path}"
        )


def _load_source(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.mode != "RGB":
            raise ValueError(f"source must be RGB, got mode {image.mode}")
        return np.asarray(image, dtype=np.uint8).copy()


def _load_proposal(path: Path, size_wh: Tuple[int, int]) -> np.ndarray:
    with Image.open(path) as image:
        if image.size != size_wh:
            raise ValueError(
                f"proposal must exactly match source size {size_wh}, got {image.size}; resizing is forbidden"
            )
        if image.mode in {"L", "1"}:
            return np.asarray(image.convert("L"), dtype=np.uint8).copy()
        if image.mode == "RGBA":
            return np.asarray(image.getchannel("A"), dtype=np.uint8).copy()
        if image.mode == "RGB":
            rgb = np.asarray(image, dtype=np.uint8)
            if not (np.array_equal(rgb[:, :, 0], rgb[:, :, 1]) and np.array_equal(rgb[:, :, 1], rgb[:, :, 2])):
                raise ValueError("RGB proposal must be grayscale in all three channels")
            return rgb[:, :, 0].copy()
        raise ValueError(f"proposal mode must be L, 1, grayscale RGB, or RGBA; got {image.mode}")


def _load_corrections(path: Path, size_wh: Tuple[int, int]) -> np.ndarray:
    with Image.open(path) as image:
        if image.mode != "RGBA":
            raise ValueError(
                f"correction overlay must be genuine RGBA, got {image.mode}; flattened overlays are rejected"
            )
        if image.size != size_wh:
            raise ValueError(
                f"correction overlay must exactly match source size {size_wh}, got {image.size}"
            )
        return np.asarray(image, dtype=np.uint8).copy()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def process_files(
    source_path: Path,
    proposal_path: Path,
    correction_path: Optional[Path],
    output_path: Path,
    metrics_path: Path,
    manifest_path: Path,
    review_board_path: Path,
    backend: str,
    config: PipelineConfig,
    allow_fallback: bool = False,
    overwrite: bool = False,
    review_max_side: int = 1200,
) -> dict[str, Any]:
    """Run candidate generation using only explicit input/output paths."""
    inputs = [source_path, proposal_path] + ([correction_path] if correction_path else [])
    outputs = [output_path, metrics_path, manifest_path, review_board_path]
    resolved_inputs = {path.expanduser().resolve() for path in inputs if path is not None}
    resolved_outputs = [path.expanduser().resolve() for path in outputs]
    if len(set(resolved_outputs)) != len(resolved_outputs):
        raise ValueError("all output, metrics, manifest, and review-board paths must differ")
    if resolved_inputs & set(resolved_outputs):
        raise ValueError("an output path would overwrite an input")
    for path in resolved_outputs:
        reject_final_path(path)
        if path.exists() and not overwrite:
            raise FileExistsError(f"output exists; pass --overwrite to replace candidate: {path}")
    if resolved_outputs[0].suffix.casefold() != ".png":
        raise ValueError("candidate output must be a PNG")
    if resolved_outputs[3].suffix.casefold() != ".png":
        raise ValueError("review board must be a PNG")
    if resolved_outputs[1].suffix.casefold() != ".json" or resolved_outputs[2].suffix.casefold() != ".json":
        raise ValueError("metrics and manifest outputs must be JSON")

    source_path = source_path.expanduser().resolve()
    proposal_path = proposal_path.expanduser().resolve()
    correction_path = correction_path.expanduser().resolve() if correction_path else None
    source_u8 = _load_source(source_path)
    size_wh = (source_u8.shape[1], source_u8.shape[0])
    proposal_u8 = _load_proposal(proposal_path, size_wh)
    corrections_u8 = _load_corrections(correction_path, size_wh) if correction_path else None

    started = time.perf_counter()
    result = run_pipeline_arrays(
        source_u8,
        proposal_u8,
        corrections_u8,
        backend,
        config,
        allow_fallback=allow_fallback,
    )
    for path in resolved_outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    save_straight_rgba(resolved_outputs[0], result.foreground_rgb, result.alpha)
    make_review_board(result.foreground_rgb, result.alpha, review_max_side).save(
        resolved_outputs[3]
    )

    input_payload = {
        "source": {
            "path": str(source_path),
            "sha256": sha256_file(source_path),
            "size_wh": list(size_wh),
            "mode": "RGB",
        },
        "proposal": {
            "path": str(proposal_path),
            "sha256": sha256_file(proposal_path),
            "size_wh": list(size_wh),
        },
        "corrections": None
        if correction_path is None
        else {
            "path": str(correction_path),
            "sha256": sha256_file(correction_path),
            "size_wh": list(size_wh),
            "mode": "RGBA",
        },
    }
    metrics = {
        "schema": "assisted-bg-metrics/v1",
        "status": "candidate-unapproved",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": input_payload,
        "config": asdict(config),
        "backend": result.backend,
        "pipeline": result.metrics,
        "elapsed_seconds": time.perf_counter() - started,
        "outputs": {
            "rgba": {
                "path": str(resolved_outputs[0]),
                "sha256": sha256_file(resolved_outputs[0]),
                "size_wh": list(size_wh),
                "mode": "RGBA-straight",
            },
            "review_board": {
                "path": str(resolved_outputs[3]),
                "sha256": sha256_file(resolved_outputs[3]),
                "backgrounds": ["white", "gray", "black", "magenta"],
            },
        },
    }
    _write_json(resolved_outputs[1], metrics)
    manifest = {
        "schema": "assisted-bg-candidate-manifest/v1",
        "status": "candidate-unapproved",
        "production_ready": False,
        "promotion_blocked_until": [
            "independent benchmark verifier passes",
            "native-resolution visual review passes on white/gray/black/magenta",
            "user approval",
        ],
        "inputs": input_payload,
        "backend": result.backend,
        "candidate": metrics["outputs"]["rgba"],
        "review_board": metrics["outputs"]["review_board"],
        "metrics": {
            "path": str(resolved_outputs[1]),
            "sha256": sha256_file(resolved_outputs[1]),
        },
    }
    _write_json(resolved_outputs[2], manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="exact-size RGB source")
    parser.add_argument("--proposal", type=Path, required=True, help="exact-size proposal alpha/mask")
    parser.add_argument("--corrections", type=Path, help="exact-size transparent RGBA corrections")
    parser.add_argument("--output", type=Path, required=True, help="candidate straight-RGBA PNG")
    parser.add_argument("--metrics", type=Path, required=True, help="candidate metrics JSON")
    parser.add_argument("--manifest", type=Path, required=True, help="candidate manifest JSON")
    parser.add_argument("--review-board", type=Path, required=True, help="four-background review PNG")
    parser.add_argument("--backend", choices=("vitmatte", "closed_form"), required=True)
    parser.add_argument("--allow-fallback", action="store_true", help="allow vitmatte -> closed_form fallback")
    parser.add_argument("--device", choices=("auto", "mps", "cpu"), default="auto")
    parser.add_argument("--proposal-fg-threshold", type=float, default=0.95)
    parser.add_argument("--proposal-bg-threshold", type=float, default=0.05)
    parser.add_argument("--inner-distance", type=int, default=3)
    parser.add_argument("--outer-distance", type=int, default=3)
    parser.add_argument("--correction-unlock-radius", type=int, default=6)
    parser.add_argument("--binary", action="store_true", help="explicitly request binary alpha")
    parser.add_argument("--binary-threshold", type=float, default=0.5)
    parser.add_argument("--residual-alpha-floor", type=float, default=0.20)
    parser.add_argument("--residual-max-adjustment", type=float, default=0.35)
    parser.add_argument(
        "--no-edge-decontamination",
        action="store_true",
        help="disable the default joint boundary RGB/alpha decontamination",
    )
    parser.add_argument(
        "--decontam-paper-distance",
        type=float,
        default=DECONTAM_PAPER_DISTANCE_8BIT,
        help=(
            "min 8-bit Euclidean distance from paper color a donor must have "
            "to trigger boundary decontamination (default: "
            f"{DECONTAM_PAPER_DISTANCE_8BIT})"
        ),
    )
    parser.add_argument("--closed-form-maxiter", type=int, default=1000)
    parser.add_argument("--vitmatte-model", default=VITMATTE_MODEL)
    parser.add_argument("--vitmatte-revision", default=VITMATTE_REVISION)
    parser.add_argument("--review-max-side", type=int, default=1200)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    config = PipelineConfig(
        proposal_fg_threshold=args.proposal_fg_threshold,
        proposal_bg_threshold=args.proposal_bg_threshold,
        inner_distance_px=args.inner_distance,
        outer_distance_px=args.outer_distance,
        correction_unlock_radius_px=args.correction_unlock_radius,
        binary=args.binary,
        binary_threshold=args.binary_threshold,
        residual_alpha_floor=args.residual_alpha_floor,
        residual_max_adjustment=args.residual_max_adjustment,
        edge_decontamination=not args.no_edge_decontamination,
        decontam_paper_distance_8bit=args.decontam_paper_distance,
        closed_form_maxiter=args.closed_form_maxiter,
        vitmatte_model=args.vitmatte_model,
        vitmatte_revision=args.vitmatte_revision,
        device=args.device,
    )
    try:
        manifest = process_files(
            source_path=args.source,
            proposal_path=args.proposal,
            correction_path=args.corrections,
            output_path=args.output,
            metrics_path=args.metrics,
            manifest_path=args.manifest,
            review_board_path=args.review_board,
            backend=args.backend,
            config=config,
            allow_fallback=args.allow_fallback,
            overwrite=args.overwrite,
            review_max_side=args.review_max_side,
        )
    except (OSError, ImportError, ValueError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
