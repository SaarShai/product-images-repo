#!/usr/bin/env python3
"""Deterministic neutral-white background keyer for controlled illustrations.

The background model is learned from border and corner pixels. Classification
is global, so genuinely background-colored gaps enclosed by line art are
removed too. This intentionally does not use a global luma threshold: color
distance from the measured key protects tinted pale watercolor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi


BG_COLORS: tuple[tuple[str, tuple[int, int, int]], ...] = (
    ("WHITE", (255, 255, 255)),
    ("GRAY", (128, 128, 128)),
    ("BLACK", (0, 0, 0)),
    ("MAGENTA", (255, 0, 255)),
)


class BackgroundModelError(ValueError):
    """The border does not support a controlled neutral-white key."""


def _srgb_to_linear(rgb01: np.ndarray) -> np.ndarray:
    return np.where(rgb01 <= 0.04045, rgb01 / 12.92, ((rgb01 + 0.055) / 1.055) ** 2.4)


def rgb_to_oklab(rgb: np.ndarray) -> np.ndarray:
    """Convert uint8/float RGB to OKLab; output L,a,b uses the 0..1 scale."""
    linear = _srgb_to_linear(rgb.astype(np.float64) / 255.0)
    lms = linear @ np.array(
        [[0.4122214708, 0.5363325363, 0.0514459929],
         [0.2119034982, 0.6806995451, 0.1073969566],
         [0.0883024619, 0.2817188376, 0.6299787005]],
        dtype=np.float64,
    ).T
    lms_root = np.cbrt(lms)
    return lms_root @ np.array(
        [[0.2104542553, 0.7936177850, -0.0040720468],
         [1.9779984951, -2.4285922050, 0.4505937099],
         [0.0259040371, 0.7827717662, -0.8086757660]],
        dtype=np.float64,
    ).T


def color_distance(rgb: np.ndarray, key_rgb: np.ndarray) -> np.ndarray:
    """Perceptual distance in approximately CIELAB-sized units."""
    lab = rgb_to_oklab(rgb)
    key_lab = rgb_to_oklab(key_rgb.reshape(1, 1, 3)).reshape(3)
    return 100.0 * np.linalg.norm(lab - key_lab, axis=-1)


def smoothstep(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def border_mask(height: int, width: int, fraction: float = 0.03) -> np.ndarray:
    band = max(2, int(round(min(height, width) * fraction)))
    mask = np.zeros((height, width), dtype=bool)
    mask[:band, :] = True
    mask[-band:, :] = True
    mask[:, :band] = True
    mask[:, -band:] = True
    return mask


def corner_pixels(rgb: np.ndarray, fraction: float = 0.03) -> np.ndarray:
    height, width = rgb.shape[:2]
    size = max(2, int(round(min(height, width) * fraction)))
    return np.concatenate(
        [
            rgb[:size, :size].reshape(-1, 3),
            rgb[:size, -size:].reshape(-1, 3),
            rgb[-size:, :size].reshape(-1, 3),
            rgb[-size:, -size:].reshape(-1, 3),
        ],
        axis=0,
    )


def estimate_background(rgb: np.ndarray, fraction: float = 0.03) -> dict[str, Any]:
    """Estimate and validate a neutral, bright, nearly uniform border key."""
    height, width = rgb.shape[:2]
    mask = border_mask(height, width, fraction)
    border = rgb[mask]
    border_chroma = border.max(axis=1).astype(np.int16) - border.min(axis=1).astype(np.int16)
    neutral_bright = (border_chroma <= 6) & (border.min(axis=1) >= 240)
    coverage = float(neutral_bright.mean())
    if coverage < 0.97:
        raise BackgroundModelError(
            f"border is not a controlled neutral-white field: neutral-bright coverage={coverage:.4f}"
        )

    samples = border[neutral_bright]
    quantized = samples // 2 * 2
    colors, counts = np.unique(quantized, axis=0, return_counts=True)
    key_rgb = colors[int(np.argmax(counts))].astype(np.uint8)
    key_spread = int(key_rgb.max()) - int(key_rgb.min())
    if int(key_rgb.min()) < 240 or key_spread > 4:
        raise BackgroundModelError(f"sampled key is not neutral white: {key_rgb.tolist()}")

    border_de = color_distance(border, key_rgb)
    p99 = float(np.percentile(border_de, 99.0))
    p999 = float(np.percentile(border_de, 99.9))
    if p999 > 3.0:
        raise BackgroundModelError(f"border is too variable for deterministic keying: p99.9={p999:.3f}")

    corner_medians = []
    height_c = max(2, int(round(min(height, width) * fraction)))
    for patch in (
        rgb[:height_c, :height_c], rgb[:height_c, -height_c:],
        rgb[-height_c:, :height_c], rgb[-height_c:, -height_c:],
    ):
        corner_medians.append(np.median(patch.reshape(-1, 3), axis=0))
    corner_disagreement = float(np.max(np.ptp(np.stack(corner_medians), axis=0)))
    if corner_disagreement > 3.0:
        raise BackgroundModelError(
            f"corner samples disagree about the background: max channel range={corner_disagreement:.2f}"
        )

    transparent_de = max(1.5, min(3.0, p999 + 0.75))
    opaque_de = transparent_de + 3.5
    return {
        "key_rgb": key_rgb,
        "border_mask": mask,
        "neutral_bright_coverage": coverage,
        "border_de_p99": p99,
        "border_de_p999": p999,
        "corner_medians": [[round(float(v), 3) for v in row] for row in corner_medians],
        "corner_max_channel_range": corner_disagreement,
        "transparent_de": transparent_de,
        "opaque_de": opaque_de,
    }


def classify_alpha(rgb: np.ndarray, model: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    distance = color_distance(rgb, model["key_rgb"])
    alpha = smoothstep(
        (distance - float(model["transparent_de"]))
        / (float(model["opaque_de"]) - float(model["transparent_de"]))
    )
    return alpha, distance


def nearest_donor(rgb: np.ndarray, donors: np.ndarray) -> np.ndarray:
    if not np.any(donors):
        return rgb.astype(np.float64)
    indices = ndi.distance_transform_edt(~donors, return_distances=False, return_indices=True)
    return rgb[tuple(indices)].astype(np.float64)


def refine_boundary_alpha(
    rgb: np.ndarray,
    alpha: np.ndarray,
    distance: np.ndarray,
    model: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Use nearest strongly-separated contour color to solve thin-edge alpha.

    The projection is applied only next to already-certain background. It
    cannot reach enclosed pale fills, so off-white watercolor is not redefined
    as a white edge merely because its color distance is modest.
    """
    secure_distance = max(12.0, float(model["opaque_de"]) + 5.0)
    certain_bg = alpha <= 0.001
    boundary_zone = ndi.binary_dilation(certain_bg, iterations=2) & ~certain_bg

    # A distance threshold alone mislabels saturated, low-alpha blends as
    # foreground donors. Restrict donors to local distance maxima: these are
    # the fully colored contour cores, even when the contour is only a few
    # pixels wide. The projection then estimates how far each edge pixel lies
    # on the measured key -> local contour color line.
    local_maximum = ndi.maximum_filter(distance, size=7, mode="nearest")
    donors = (distance >= secure_distance) & (distance >= local_maximum - 1e-6)
    donor = nearest_donor(rgb, donors)
    key = model["key_rgb"].astype(np.float64).reshape(1, 1, 3)
    observed_vector = rgb.astype(np.float64) - key
    donor_vector = donor - key
    denominator = np.sum(donor_vector * donor_vector, axis=2)
    projected = np.sum(observed_vector * donor_vector, axis=2) / np.maximum(denominator, 1.0)
    projected = np.clip(projected, 0.0, 1.0)
    # Away from the measured key boundary, any color distinguishable from the
    # border envelope is foreground. This is the safeguard that keeps pale,
    # tinted watercolor opaque instead of treating lightness as transparency.
    refined = np.ones_like(alpha)
    refined[certain_bg] = 0.0
    refined[boundary_zone] = projected[boundary_zone]
    return refined, donors, {
        "method": "nearest_local_maximum_contour_projection_in_2px_background_band",
        "secure_distance": round(float(secure_distance), 4),
        "secure_donor_pixel_count": int(donors.sum()),
        "refined_pixel_count": int(boundary_zone.sum()),
    }


def unmix_neutral_key(
    rgb: np.ndarray,
    alpha: np.ndarray,
    key_rgb: np.ndarray,
    donor_mask: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Regularized straight-RGB recovery for a neutral key, with no hue despill."""
    observed = rgb.astype(np.float64)
    key = key_rgb.astype(np.float64).reshape(1, 1, 3)
    donor = nearest_donor(rgb, donor_mask)
    a = np.clip(alpha, 1e-4, 1.0)[..., None]
    residual = observed - (1.0 - a) * key
    regularizer = (0.10 * (1.0 - a)) ** 2
    recovered = (a * residual + regularizer * donor) / (a * a + regularizer)
    recovered = np.clip(recovered, 0.0, 255.0)

    band = (alpha > 0.0) & (alpha < 1.0)
    out = observed.copy()
    out[band] = recovered[band]
    # Meaningful hidden RGB avoids white-key poison if a later RGB upscaler sees it.
    out[alpha <= 0.0] = donor[alpha <= 0.0]
    out = np.clip(np.round(out), 0, 255).astype(np.uint8)
    return out, {
        "method": "donor_regularized_neutral_key_unmix",
        "band_pixel_count": int(band.sum()),
        "hidden_rgb_fill": "nearest_strong-color-distance_donor",
        "hue_specific_despill": False,
    }


def composite(rgba: np.ndarray, background: Sequence[int]) -> np.ndarray:
    rgb = rgba[..., :3].astype(np.float64)
    alpha = rgba[..., 3:4].astype(np.float64) / 255.0
    bg = np.asarray(background, dtype=np.float64).reshape(1, 1, 3)
    return np.clip(np.round(rgb * alpha + bg * (1.0 - alpha)), 0, 255).astype(np.uint8)


def transparent_topology(alpha_u8: np.ndarray) -> dict[str, Any]:
    transparent = alpha_u8 <= 1
    labels, count = ndi.label(transparent, structure=np.ones((3, 3), dtype=np.uint8))
    border_ids = np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))
    enclosed = transparent & ~np.isin(labels, border_ids)
    enclosed_labels, enclosed_count = ndi.label(enclosed, structure=np.ones((3, 3), dtype=np.uint8))
    areas = np.bincount(enclosed_labels.ravel())[1:] if enclosed_count else np.array([], dtype=int)
    return {
        "transparent_component_count": int(count),
        "enclosed_transparent_component_count": int(enclosed_count),
        "enclosed_transparent_pixel_count": int(enclosed.sum()),
        "largest_enclosed_transparent_area": int(areas.max(initial=0)),
    }


def build_review_board(rgba: np.ndarray) -> Image.Image:
    height, width = rgba.shape[:2]
    label_height = 34
    board = Image.new("RGB", (width * 2, (height + label_height) * 2), "white")
    draw = ImageDraw.Draw(board)
    for index, (label, color) in enumerate(BG_COLORS):
        x = (index % 2) * width
        y = (index // 2) * (height + label_height)
        board.paste(Image.fromarray(composite(rgba, color), "RGB"), (x, y + label_height))
        draw.rectangle((x, y, x + width, y + label_height), fill=(245, 245, 245))
        draw.text((x + 10, y + 9), label, fill=(15, 15, 15))
    return board


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def key_array(rgb: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("rgb must be an HxWx3 uint8 array")
    model = estimate_background(rgb)
    alpha, distance = classify_alpha(rgb, model)
    alpha, donor_mask, alpha_refinement = refine_boundary_alpha(rgb, alpha, distance, model)
    straight_rgb, unmix = unmix_neutral_key(rgb, alpha, model["key_rgb"], donor_mask)
    alpha_u8 = np.clip(np.round(alpha * 255.0), 0, 255).astype(np.uint8)
    rgba = np.dstack((straight_rgb, alpha_u8))

    transparent = alpha_u8 <= 1
    opaque = alpha_u8 >= 254
    soft = ~(transparent | opaque)
    border_occupancy = float((alpha_u8[model["border_mask"]] > 127).mean())
    reconstructed = composite(rgba, model["key_rgb"])
    diff = np.abs(reconstructed.astype(np.int16) - rgb.astype(np.int16))

    profile_failures = []
    if not transparent.any() or not opaque.any():
        profile_failures.append("alpha lacks both fully transparent and fully opaque pixels")
    if not soft.any():
        profile_failures.append("alpha lacks an antialiased transition band")
    if float(soft.mean()) > 0.08:
        profile_failures.append(f"soft-alpha band exceeds 8% of image ({100 * soft.mean():.3f}%)")
    if border_occupancy > 0.005:
        profile_failures.append(f"foreground occupies too much border ({100 * border_occupancy:.3f}%)")

    metrics: dict[str, Any] = {
        "background_model": {
            "key_rgb": model["key_rgb"].astype(int).tolist(),
            "neutral_bright_border_coverage": round(float(model["neutral_bright_coverage"]), 6),
            "border_de_p99": round(float(model["border_de_p99"]), 4),
            "border_de_p999": round(float(model["border_de_p999"]), 4),
            "corner_medians": model["corner_medians"],
            "corner_max_channel_range": round(float(model["corner_max_channel_range"]), 4),
            "transparent_de": round(float(model["transparent_de"]), 4),
            "opaque_de": round(float(model["opaque_de"]), 4),
        },
        "alpha": {
            "min": int(alpha_u8.min()),
            "max": int(alpha_u8.max()),
            "unique": int(np.unique(alpha_u8).size),
            "transparent_pct": round(100.0 * float(transparent.mean()), 4),
            "soft_pct": round(100.0 * float(soft.mean()), 4),
            "opaque_pct": round(100.0 * float(opaque.mean()), 4),
            "border_foreground_occupancy_pct": round(100.0 * border_occupancy, 6),
        },
        "topology": transparent_topology(alpha_u8),
        "unmix": unmix,
        "alpha_refinement": alpha_refinement,
        "reconstruction_on_sampled_key": {
            "mae": round(float(diff.mean()), 4),
            "p95": int(np.percentile(diff, 95)),
            "max": int(diff.max(initial=0)),
        },
        "gates": {
            "background_model_valid": True,
            "rgba_profile_valid": not profile_failures,
            "machine_pass": not profile_failures,
            "failures": profile_failures,
            "visual_approval": "NOT_RUN",
        },
        "distance_summary": {
            "p50": round(float(np.percentile(distance, 50)), 4),
            "p95": round(float(np.percentile(distance, 95)), 4),
            "p99": round(float(np.percentile(distance, 99)), 4),
        },
    }
    return rgba, metrics


def process(input_path: Path, output_path: Path, json_path: Path, review_path: Path) -> dict[str, Any]:
    with Image.open(input_path) as image:
        if image.mode != "RGB":
            raise ValueError(f"input must be RGB, got {image.mode}")
        rgb = np.asarray(image, dtype=np.uint8)
    rgba, metrics = key_array(rgb)
    metrics.update(
        {
            "input": str(input_path),
            "input_sha256": sha256_file(input_path),
            "output": str(output_path),
            "review_board": str(review_path),
            "width": int(rgb.shape[1]),
            "height": int(rgb.shape[0]),
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(output_path)
    build_review_board(rgba).save(review_path)
    json_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    return metrics


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--review-board", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        metrics = process(args.input, args.output, args.json, args.review_board)
    except (OSError, ValueError, BackgroundModelError) as exc:
        print(json.dumps({"machine_pass": False, "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(metrics, indent=2))
    return 0 if metrics["gates"]["machine_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
