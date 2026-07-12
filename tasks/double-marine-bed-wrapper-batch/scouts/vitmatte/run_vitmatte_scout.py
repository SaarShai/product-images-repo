#!/usr/bin/env python3
"""One-shot native-resolution ViTMatte-S feasibility scout for image 14.

This is deliberately not a background-removal pipeline.  An existing, rejected
candidate alpha is used only to construct a conservative trimap.  The script
runs one ViTMatte architecture attempt, preserves its soft alpha prediction,
and compares source RGB with PyMatting foreground-color recovery.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import sys
import threading
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import pymatting
import torch
import transformers
from PIL import Image, ImageDraw, ImageFont
from pymatting import estimate_foreground_ml
from transformers import VitMatteForImageMatting, VitMatteImageProcessor


PRODUCT_IMAGES = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
SOURCE = PRODUCT_IMAGES / "ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
SEED_CANDIDATE = (
    PRODUCT_IMAGES
    / "Images/candidates/image14-research/fusion-soft-v1/"
    "14-soft-flood-edge-unmatte-x4.png"
)
OUT_DIR = (
    PRODUCT_IMAGES
    / "Images/candidates/image14-research/vitmatte-scout"
)
MODEL_ID = "hustvl/vitmatte-small-composition-1k"
MODEL_REVISION = "6a58ad7646403c1df626fbd746900aec7361ea1d"

# Defect coordinates originated on the x8 (7528x13376) review surface.  Each
# board below is a 96x96 crop in the native 941x1672 coordinate system.
ROIS = {
    "cutout_01": {"center_native": (286, 1001), "evidence_x8": (2175, 7911, 232, 200)},
    "cutout_02": {"center_native": (567, 889), "evidence_x8": (4447, 7013, 181, 200)},
    "fringe_00": {"center_native": (880, 1072), "evidence_x8": (6912, 8448, 256, 256)},
    "outer_soft": {"center_native": (208, 208), "evidence_x8": (1536, 1536, 256, 256)},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def alpha_summary(alpha: np.ndarray) -> dict[str, Any]:
    a = np.asarray(alpha, dtype=np.float32)
    return {
        "min": float(a.min()),
        "max": float(a.max()),
        "mean": float(a.mean()),
        "percentiles": {
            str(p): float(np.percentile(a, p))
            for p in (0, 1, 5, 25, 50, 75, 95, 99, 100)
        },
        "exact_zero_pct": float(100.0 * np.mean(a == 0.0)),
        "exact_one_pct": float(100.0 * np.mean(a == 1.0)),
        "soft_pct": float(100.0 * np.mean((a > 0.0) & (a < 1.0))),
    }


def build_trimap(seed_alpha_x4: np.ndarray, size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Downsample seed alpha explicitly and form conservative sure sets."""
    width, height = size
    seed_native = cv2.resize(
        seed_alpha_x4.astype(np.float32) / 255.0,
        (width, height),
        interpolation=cv2.INTER_AREA,
    )
    foreground = (seed_native >= 0.98).astype(np.uint8)
    background = (seed_native <= 0.02).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    sure_fg = cv2.erode(foreground, kernel, iterations=1).astype(bool)
    sure_bg = cv2.erode(background, kernel, iterations=1).astype(bool)
    trimap = np.full((height, width), 128, dtype=np.uint8)
    trimap[sure_bg] = 0
    trimap[sure_fg] = 255
    assert not np.any(sure_bg & sure_fg)
    return seed_native, trimap


class MemorySampler:
    def __init__(self, interval_s: float = 0.02) -> None:
        self.interval_s = interval_s
        self.stop_event = threading.Event()
        self.max_current = 0
        self.max_driver = 0
        self.thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self.stop_event.is_set():
            if torch.backends.mps.is_available():
                try:
                    self.max_current = max(self.max_current, torch.mps.current_allocated_memory())
                    self.max_driver = max(self.max_driver, torch.mps.driver_allocated_memory())
                except RuntimeError:
                    pass
            self.stop_event.wait(self.interval_s)

    def __enter__(self) -> "MemorySampler":
        self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop_event.set()
        self.thread.join()


def load_model(device: torch.device) -> tuple[VitMatteImageProcessor, VitMatteForImageMatting, float]:
    start = time.perf_counter()
    processor = VitMatteImageProcessor.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        local_files_only=True,
    )
    model = VitMatteForImageMatting.from_pretrained(
        MODEL_ID,
        revision=MODEL_REVISION,
        local_files_only=True,
    ).eval()
    model.to(device)
    if device.type == "mps":
        torch.mps.synchronize()
    return processor, model, time.perf_counter() - start


def run_model(image: Image.Image, trimap: Image.Image) -> tuple[np.ndarray, dict[str, Any]]:
    requested = "mps" if torch.backends.mps.is_available() else "cpu"
    device = torch.device(requested)
    fallback_error: str | None = None
    processor: VitMatteImageProcessor | None = None
    model: VitMatteForImageMatting | None = None

    with MemorySampler() as memory:
        try:
            processor, model, load_s = load_model(device)
            preprocess_start = time.perf_counter()
            inputs = processor(images=image, trimaps=trimap, return_tensors="pt")
            pixel_values = inputs["pixel_values"].to(device)
            preprocess_s = time.perf_counter() - preprocess_start
            forward_start = time.perf_counter()
            with torch.inference_mode():
                output = model(pixel_values=pixel_values).alphas
            if device.type == "mps":
                torch.mps.synchronize()
            forward_s = time.perf_counter() - forward_start
        except (RuntimeError, NotImplementedError) as error:
            if device.type != "mps":
                raise
            fallback_error = f"{type(error).__name__}: {error}"
            del processor, model
            torch.mps.empty_cache()
            device = torch.device("cpu")
            processor, model, load_s = load_model(device)
            preprocess_start = time.perf_counter()
            inputs = processor(images=image, trimaps=trimap, return_tensors="pt")
            pixel_values = inputs["pixel_values"]
            preprocess_s = time.perf_counter() - preprocess_start
            forward_start = time.perf_counter()
            with torch.inference_mode():
                output = model(pixel_values=pixel_values).alphas
            forward_s = time.perf_counter() - forward_start

        padded_shape = list(pixel_values.shape)
        alpha = output[0, 0, : image.height, : image.width].detach().float().cpu().numpy()

    alpha = np.clip(alpha, 0.0, 1.0)
    run_info = {
        "device_requested": requested,
        "device_used": device.type,
        "mps_fallback_error": fallback_error,
        "processor_pixel_values_shape": padded_shape,
        "source_shape_hw": [image.height, image.width],
        "padding_bottom_px": int(padded_shape[-2] - image.height),
        "padding_right_px": int(padded_shape[-1] - image.width),
        "model_load_seconds": load_s,
        "preprocess_seconds": preprocess_s,
        "forward_seconds": forward_s,
        "mps_peak_current_allocated_bytes_sampled": memory.max_current,
        "mps_peak_driver_allocated_bytes_sampled": memory.max_driver,
        "rss_peak_bytes_ru_maxrss": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
    }
    return alpha, run_info


def save_rgba(path: Path, rgb: np.ndarray, alpha: np.ndarray) -> None:
    rgb8 = np.clip(np.rint(rgb * 255.0), 0, 255).astype(np.uint8)
    alpha8 = np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8)
    rgba = np.dstack([rgb8, alpha8])
    Image.fromarray(rgba, "RGBA").save(path)


def composite(rgb: np.ndarray, alpha: np.ndarray, background: tuple[int, int, int]) -> np.ndarray:
    bg = np.asarray(background, dtype=np.float32) / 255.0
    result = rgb * alpha[:, :, None] + bg[None, None, :] * (1.0 - alpha[:, :, None])
    return np.clip(np.rint(result * 255.0), 0, 255).astype(np.uint8)


def crop_xyxy(center: tuple[int, int], width: int, height: int, crop_size: int = 96) -> tuple[int, int, int, int]:
    cx, cy = center
    half = crop_size // 2
    x0 = max(0, min(width - crop_size, cx - half))
    y0 = max(0, min(height - crop_size, cy - half))
    return x0, y0, x0 + crop_size, y0 + crop_size


def make_roi_board(
    path: Path,
    name: str,
    box: tuple[int, int, int, int],
    source_rgb: np.ndarray,
    recovered_rgb: np.ndarray,
    alpha: np.ndarray,
) -> None:
    backgrounds = [
        ("white", (255, 255, 255)),
        ("gray", (128, 128, 128)),
        ("black", (0, 0, 0)),
        ("magenta", (255, 0, 255)),
    ]
    x0, y0, x1, y1 = box
    scale = 3
    tile = (x1 - x0) * scale
    label_h = 28
    board = Image.new("RGB", (tile * 4, label_h * 2 + tile * 2), "white")
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    for row, (row_name, rgb) in enumerate((('source RGB', source_rgb), ('recovered RGB', recovered_rgb))):
        y_label = row * (label_h + tile)
        for col, (bg_name, bg) in enumerate(backgrounds):
            comp = composite(rgb, alpha, bg)[y0:y1, x0:x1]
            tile_image = Image.fromarray(comp, "RGB").resize((tile, tile), Image.Resampling.NEAREST)
            board.paste(tile_image, (col * tile, y_label + label_h))
            draw.text((col * tile + 5, y_label + 7), f"{row_name} / {bg_name}", fill=(0, 0, 0), font=font)
    draw.rectangle((0, 0, board.width - 1, board.height - 1), outline=(0, 0, 0))
    board.save(path)


def make_full_board(path: Path, source_rgb: np.ndarray, recovered_rgb: np.ndarray, alpha: np.ndarray) -> None:
    rows = []
    for rgb in (source_rgb, recovered_rgb):
        gray = composite(rgb, alpha, (128, 128, 128))
        black = composite(rgb, alpha, (0, 0, 0))
        rows.append(np.concatenate([gray, black], axis=1))
    Image.fromarray(np.concatenate(rows, axis=0), "RGB").save(path)


def roi_metrics(alpha: np.ndarray, boxes: dict[str, tuple[int, int, int, int]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, (x0, y0, x1, y1) in boxes.items():
        patch = alpha[y0:y1, x0:x1]
        result[name] = {"box_native_xyxy": [x0, y0, x1, y1], "alpha": alpha_summary(patch)}
    return result


def main() -> None:
    started = time.perf_counter()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    source_image = Image.open(SOURCE).convert("RGB")
    source_rgb = np.asarray(source_image, dtype=np.float32) / 255.0
    candidate_image = Image.open(SEED_CANDIDATE).convert("RGBA")
    candidate_alpha_x4 = np.asarray(candidate_image.getchannel("A"), dtype=np.uint8)
    seed_native, trimap = build_trimap(candidate_alpha_x4, source_image.size)
    Image.fromarray(trimap, "L").save(OUT_DIR / "14-vitmatte-scout-trimap.png")
    Image.fromarray(np.clip(np.rint(seed_native * 255.0), 0, 255).astype(np.uint8), "L").save(
        OUT_DIR / "14-vitmatte-scout-seed-alpha-native.png"
    )

    alpha, run_info = run_model(source_image, Image.fromarray(trimap, "L"))
    foreground_started = time.perf_counter()
    recovered_rgb = np.clip(estimate_foreground_ml(source_rgb, alpha), 0.0, 1.0)
    foreground_seconds = time.perf_counter() - foreground_started

    source_rgba_path = OUT_DIR / "14-vitmatte-scout-source-rgb.png"
    recovered_rgba_path = OUT_DIR / "14-vitmatte-scout-recovered-rgb.png"
    save_rgba(source_rgba_path, source_rgb, alpha)
    save_rgba(recovered_rgba_path, recovered_rgb, alpha)
    Image.fromarray(np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8), "L").save(
        OUT_DIR / "14-vitmatte-scout-alpha.png"
    )

    boxes = {
        name: crop_xyxy(tuple(spec["center_native"]), source_image.width, source_image.height)
        for name, spec in ROIS.items()
    }
    for name, box in boxes.items():
        make_roi_board(
            OUT_DIR / f"review-{name}-four-backgrounds.png",
            name,
            box,
            source_rgb,
            recovered_rgb,
            alpha,
        )
    make_full_board(OUT_DIR / "review-full-gray-black-source-vs-recovered.png", source_rgb, recovered_rgb, alpha)

    source_saved_alpha = np.asarray(Image.open(source_rgba_path).getchannel("A"), dtype=np.uint8)
    recovered_saved_alpha = np.asarray(Image.open(recovered_rgba_path).getchannel("A"), dtype=np.uint8)
    alpha_identical = bool(np.array_equal(source_saved_alpha, recovered_saved_alpha))
    if not alpha_identical:
        raise AssertionError("source-RGB and recovered-RGB alpha channels differ")

    sure_bg = trimap == 0
    sure_fg = trimap == 255
    unknown = trimap == 128
    relevant = alpha > 0.01
    rgb_delta = np.abs(recovered_rgb - source_rgb)
    metrics = {
        "status": "scout-completed",
        "claim_boundary": "Feasibility evidence only; seed candidate is not ground truth and visual quality is not accepted here.",
        "model": {"id": MODEL_ID, "revision": MODEL_REVISION},
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "pymatting": getattr(pymatting, "__version__", "unknown"),
            "opencv": cv2.__version__,
            "mps_built": torch.backends.mps.is_built(),
            "mps_available": torch.backends.mps.is_available(),
        },
        "inputs": {
            "source": str(SOURCE),
            "source_sha256": sha256(SOURCE),
            "source_size_wh": list(source_image.size),
            "seed_candidate": str(SEED_CANDIDATE),
            "seed_candidate_sha256": sha256(SEED_CANDIDATE),
            "seed_candidate_size_wh": list(candidate_image.size),
            "seed_resample": "cv2.INTER_AREA x4-to-native; explicit scout-only operation",
        },
        "trimap": {
            "construction": "seed alpha <=0.02 / >=0.98, then 9x9 elliptical erosion of each sure set; remainder unknown",
            "not_ground_truth": True,
            "sure_bg_pct": float(100.0 * sure_bg.mean()),
            "unknown_pct": float(100.0 * unknown.mean()),
            "sure_fg_pct": float(100.0 * sure_fg.mean()),
        },
        "run": run_info,
        "foreground_recovery_seconds": foreground_seconds,
        "total_seconds": time.perf_counter() - started,
        "alpha": alpha_summary(alpha),
        "alpha_by_trimap": {
            "sure_bg": alpha_summary(alpha[sure_bg]),
            "unknown": alpha_summary(alpha[unknown]),
            "sure_fg": alpha_summary(alpha[sure_fg]),
        },
        "foreground_recovery": {
            "alpha_relevant_pixel_pct": float(100.0 * relevant.mean()),
            "mean_absolute_rgb_delta_alpha_gt_0_01": float(rgb_delta[relevant].mean()),
            "p95_absolute_rgb_delta_alpha_gt_0_01": float(np.percentile(rgb_delta[relevant], 95)),
        },
        "roi_metrics": roi_metrics(alpha, boxes),
        "rgba_alpha_identical": alpha_identical,
        "outputs": sorted(str(path) for path in OUT_DIR.glob("*")),
    }
    (OUT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
