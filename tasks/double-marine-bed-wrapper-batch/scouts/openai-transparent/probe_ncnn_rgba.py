#!/usr/bin/env python3
"""Run the one authorized ncnn RGBA behavior probe and record exact evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image


REPO = Path(__file__).resolve().parents[4]
BIN = REPO / "tasks/marine-pod-upscale/tools/realesrgan-full/realesrgan-ncnn-vulkan"
MODELS = REPO / "tasks/marine-pod-upscale/tools/realesrgan-full/models"
OUT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/"
    "openai-transparent-image14/ncnn-rgba-probe"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_fixture(size: int = 64) -> np.ndarray:
    y, x = np.mgrid[:size, :size].astype(np.float32)
    rgb = np.stack(
        [
            30.0 + 220.0 * x / (size - 1),
            25.0 + 210.0 * y / (size - 1),
            235.0 - 180.0 * x / (size - 1),
        ],
        axis=2,
    )
    radius = np.sqrt((x - 31.5) ** 2 + (y - 31.5) ** 2)
    alpha = np.clip((27.0 - radius) / 9.0, 0.0, 1.0)
    alpha[10:20, 6:30] = np.maximum(alpha[10:20, 6:30], np.linspace(0, 1, 24)[None, :])
    return np.dstack([np.rint(rgb), np.rint(alpha * 255.0)]).astype(np.uint8)


def alpha_stats(alpha: np.ndarray) -> dict[str, float | int]:
    return {
        "min": int(alpha.min()),
        "max": int(alpha.max()),
        "unique": int(np.unique(alpha).size),
        "zero_pct": float(100.0 * np.mean(alpha == 0)),
        "soft_pct": float(100.0 * np.mean((alpha > 0) & (alpha < 255))),
        "opaque_pct": float(100.0 * np.mean(alpha == 255)),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    input_path = OUT / "synthetic-rgba-64.png"
    output_path = OUT / "synthetic-rgba-64-ncnn-x4.png"
    Image.fromarray(make_fixture(), "RGBA").save(input_path)

    command = [
        str(BIN),
        "-i",
        str(input_path),
        "-o",
        str(output_path),
        "-n",
        "realesrgan-x4plus",
        "-m",
        str(MODELS),
        "-s",
        "4",
        "-t",
        "64",
        "-f",
        "png",
    ]
    started = time.perf_counter()
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    elapsed = time.perf_counter() - started

    source = Image.open(input_path).convert("RGBA")
    metrics: dict[str, object] = {
        "probe_count": 1,
        "command": command,
        "returncode": result.returncode,
        "elapsed_seconds": elapsed,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "input": {
            "path": str(input_path),
            "sha256": digest(input_path),
            "mode": "RGBA",
            "size": list(source.size),
            "alpha": alpha_stats(np.asarray(source.getchannel("A"))),
        },
        "output_exists": output_path.is_file(),
    }
    if output_path.is_file():
        output = Image.open(output_path)
        output_record: dict[str, object] = {
            "path": str(output_path),
            "sha256": digest(output_path),
            "mode": output.mode,
            "bands": list(output.getbands()),
            "size": list(output.size),
        }
        if "A" in output.getbands():
            actual = np.asarray(output.getchannel("A"), dtype=np.float32)
            output_record["alpha"] = alpha_stats(actual.astype(np.uint8))
            comparisons: dict[str, float] = {}
            for name, method in (
                ("nearest", Image.Resampling.NEAREST),
                ("bilinear", Image.Resampling.BILINEAR),
                ("bicubic", Image.Resampling.BICUBIC),
                ("lanczos", Image.Resampling.LANCZOS),
            ):
                expected = np.asarray(source.getchannel("A").resize(output.size, method), dtype=np.float32)
                comparisons[f"mae_vs_{name}"] = float(np.mean(np.abs(actual - expected)))
                comparisons[f"max_abs_vs_{name}"] = float(np.max(np.abs(actual - expected)))
            output_record["alpha_resample_comparisons"] = comparisons
        metrics["output"] = output_record

    metrics_path = OUT / "probe-metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
