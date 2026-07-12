#!/usr/bin/env python3
"""Build deterministic evidence artifacts for the bounded Photoshop scout."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


SOURCE = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
)
OUT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/image14-research/photoshop-scout"
)
AUTO = OUT / "image14-photoshop-auto-mask.png"
DECONT = OUT / "image14-photoshop-auto-mask-remove-white-matte.png"

# Coordinates are the established image14 x8 review regions. Convert their
# half-open bounds to the original 941x1672 source with floor(start)/ceil(end).
CROPS_X8 = {
    "cut00": (3601, 6253, 320, 400),
    "fringe_pink": (4355 - 128, 5013 - 128, 256, 256),
    "enclosed_tri": (6452 - 128, 5548 - 128, 256, 256),
}

BACKGROUNDS = {
    "white": (255, 255, 255, 255),
    "gray": (128, 128, 128, 255),
    "black": (0, 0, 0, 255),
    "magenta": (255, 0, 255, 255),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def original_box(box_x8: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, width, height = box_x8
    return (x // 8, y // 8, (x + width + 7) // 8, (y + height + 7) // 8)


def composite(image: Image.Image, color: tuple[int, int, int, int]) -> Image.Image:
    background = Image.new("RGBA", image.size, color)
    return Image.alpha_composite(background, image).convert("RGB")


def board(images: list[Image.Image], columns: int) -> Image.Image:
    width, height = images[0].size
    rows = (len(images) + columns - 1) // columns
    result = Image.new("RGB", (columns * width, rows * height), (64, 64, 64))
    for index, image in enumerate(images):
        result.paste(image, ((index % columns) * width, (index // columns) * height))
    return result


def alpha_stats(image: Image.Image) -> dict[str, object]:
    alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
    transparent = alpha == 0
    opaque = alpha == 255
    partial = (~transparent) & (~opaque)
    count = int(alpha.size)
    components, _, component_stats, _ = cv2.connectedComponentsWithStats(
        transparent.astype(np.uint8), connectivity=8
    )
    enclosed_components = 0
    for index in range(1, components):
        x, y, width, height, _ = component_stats[index]
        touches_border = x == 0 or y == 0 or x + width == alpha.shape[1] or y + height == alpha.shape[0]
        if not touches_border:
            enclosed_components += 1
    return {
        "min": int(alpha.min()),
        "max": int(alpha.max()),
        "transparent_pixels": int(transparent.sum()),
        "transparent_percent": round(float(transparent.sum() * 100 / count), 6),
        "opaque_pixels": int(opaque.sum()),
        "opaque_percent": round(float(opaque.sum() * 100 / count), 6),
        "partial_pixels": int(partial.sum()),
        "partial_percent": round(float(partial.sum() * 100 / count), 6),
        "unique_alpha_values": int(np.unique(alpha).size),
        "transparent_components_total_excluding_background_label": int(components - 1),
        "transparent_enclosed_components": int(enclosed_components),
    }


def crop_stats(image: Image.Image, box: tuple[int, int, int, int]) -> dict[str, object]:
    rgba = np.asarray(image.crop(box), dtype=np.uint8)
    alpha = rgba[..., 3]
    partial = (alpha > 0) & (alpha < 255)
    near_white = (rgba[..., :3].min(axis=2) >= 245) & partial
    pixels = int(alpha.size)
    return {
        "box_original": list(box),
        "size": [int(alpha.shape[1]), int(alpha.shape[0])],
        "transparent_percent": round(float((alpha == 0).sum() * 100 / pixels), 6),
        "opaque_percent": round(float((alpha == 255).sum() * 100 / pixels), 6),
        "partial_percent": round(float(partial.sum() * 100 / pixels), 6),
        "near_white_partial_pixels": int(near_white.sum()),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE).convert("RGB")
    auto = Image.open(AUTO).convert("RGBA")
    decont = Image.open(DECONT).convert("RGBA")
    if auto.size != source.size or decont.size != source.size:
        raise RuntimeError(
            f"size mismatch: source={source.size} auto={auto.size} decont={decont.size}"
        )

    auto_alpha = np.asarray(auto.getchannel("A"), dtype=np.uint8)
    decont_alpha = np.asarray(decont.getchannel("A"), dtype=np.uint8)
    auto_rgb = np.asarray(auto, dtype=np.uint8)[..., :3]
    decont_rgb = np.asarray(decont, dtype=np.uint8)[..., :3]
    source_rgb = np.asarray(source, dtype=np.uint8)
    alpha_equal = bool(np.array_equal(auto_alpha, decont_alpha))
    rgb_delta = np.abs(auto_rgb.astype(np.int16) - decont_rgb.astype(np.int16))
    changed_rgb = np.any(rgb_delta > 0, axis=2)
    visible = auto_alpha > 0
    opaque = auto_alpha == 255
    partial = visible & (~opaque)
    transparent = auto_alpha == 0

    def delta_subset(mask: np.ndarray) -> dict[str, object]:
        pixels = int(mask.sum())
        changed = int((changed_rgb & mask).sum())
        subset_delta = rgb_delta[mask]
        return {
            "pixels": pixels,
            "changed_pixels": changed,
            "changed_percent": round(float(changed * 100 / pixels), 6) if pixels else 0.0,
            "mean_absolute_channel_delta": round(float(subset_delta.mean()), 6) if pixels else 0.0,
            "max_channel_delta": int(subset_delta.max()) if pixels else 0,
        }

    auto.getchannel("A").save(OUT / "image14-photoshop-auto-mask-alpha.png")

    distance_from_white = np.linalg.norm(255.0 - source_rgb.astype(np.float32), axis=2)
    high_confidence_deleted = (auto_alpha <= 8) & (distance_from_white >= 40.0)
    possible_deleted = (auto_alpha <= 8) & (distance_from_white >= 20.0)
    opaque_near_white = (auto_alpha >= 247) & (source_rgb.min(axis=2) >= 248)

    deletion_overlay = source_rgb.copy()
    deletion_overlay[high_confidence_deleted] = np.array([255, 0, 0], dtype=np.uint8)
    Image.fromarray(deletion_overlay).save(
        OUT / "diagnostic-high-confidence-deletion-overlay-red.png"
    )
    background_overlay = source_rgb.copy()
    background_overlay[opaque_near_white] = np.array([0, 255, 255], dtype=np.uint8)
    Image.fromarray(background_overlay).save(
        OUT / "diagnostic-opaque-near-white-overlay-cyan.png"
    )

    full_panels: list[Image.Image] = []
    for candidate in (auto, decont):
        for color in BACKGROUNDS.values():
            full_panels.append(composite(candidate, color))
    board(full_panels, columns=4).save(OUT / "full-multibackground-board-native.png")

    crop_manifest: dict[str, object] = {}
    for name, box_x8 in CROPS_X8.items():
        box = original_box(box_x8)
        crop_panels: list[Image.Image] = []
        for candidate in (auto.crop(box), decont.crop(box)):
            for color in BACKGROUNDS.values():
                crop_panels.append(composite(candidate, color))
        native_board = board(crop_panels, columns=4)
        native_path = OUT / f"crop-{name}-multibackground-board-native.png"
        native_board.save(native_path)
        native_board.resize(
            (native_board.width * 8, native_board.height * 8), Image.Resampling.NEAREST
        ).save(OUT / f"crop-{name}-multibackground-board-review-8x.png")
        crop_manifest[name] = {
            "box_x8": list(box_x8),
            "box_original": list(box),
            "layout": "row 1 auto, row 2 Remove White Matte; columns white, gray, black, magenta",
            "auto": crop_stats(auto, box),
            "remove_white_matte": crop_stats(decont, box),
        }

    analysis = {
        "source": {
            "path": str(SOURCE),
            "sha256": sha256(SOURCE),
            "mode": source.mode,
            "size": list(source.size),
        },
        "photoshop": {
            "version": "27.8.0",
            "automatic_attempts": 1,
            "automatic_command": "autoCutout(sampleAllLayers=false) + make revealSelection user mask",
            "select_subject_processing": "UNVERIFIED (descriptor does not expose Device/Cloud)",
            "decontamination_attempts": 1,
            "decontamination_command": "apply existing layer mask + removeWhiteMatte",
        },
        "outputs": {
            "auto": {
                "path": str(AUTO),
                "sha256": sha256(AUTO),
                "mode": auto.mode,
                "size": list(auto.size),
                "alpha": alpha_stats(auto),
            },
            "remove_white_matte": {
                "path": str(DECONT),
                "sha256": sha256(DECONT),
                "mode": decont.mode,
                "size": list(decont.size),
                "alpha": alpha_stats(decont),
            },
        },
        "separation_check": {
            "alpha_arrays_equal": alpha_equal,
            "alpha_differing_pixels": int((auto_alpha != decont_alpha).sum()),
            "rgb_changed_pixels": int(changed_rgb.sum()),
            "rgb_changed_percent": round(float(changed_rgb.sum() * 100 / changed_rgb.size), 6),
            "rgb_max_channel_delta": int(rgb_delta.max()),
            "rgb_mean_absolute_channel_delta": round(float(rgb_delta.mean()), 6),
            "visible_pixels": delta_subset(visible),
            "opaque_pixels": delta_subset(opaque),
            "partial_pixels": delta_subset(partial),
            "transparent_pixels": delta_subset(transparent),
        },
        "heuristic_diagnostics_not_ground_truth": {
            "high_confidence_deleted_rule": "alpha<=8 and RGB Euclidean distance from white>=40",
            "high_confidence_deleted_pixels": int(high_confidence_deleted.sum()),
            "possible_deleted_rule": "alpha<=8 and RGB Euclidean distance from white>=20",
            "possible_deleted_pixels": int(possible_deleted.sum()),
            "opaque_near_white_rule": "alpha>=247 and every source RGB channel>=248",
            "opaque_near_white_pixels": int(opaque_near_white.sum()),
            "warning": "These are review proposals only; pale paint and paper overlap, so they are not semantic pass/fail evidence.",
        },
        "boards": {
            "full": {
                "path": str(OUT / "full-multibackground-board-native.png"),
                "layout": "row 1 auto, row 2 Remove White Matte; columns white, gray, black, magenta",
                "panel_size": list(source.size),
            },
            "crops": crop_manifest,
        },
    }
    (OUT / "manifest.json").write_text(json.dumps(analysis, indent=2) + "\n")
    print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    main()
