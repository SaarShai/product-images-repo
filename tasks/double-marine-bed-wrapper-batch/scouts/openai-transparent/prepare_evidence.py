#!/usr/bin/env python3
"""Freeze OpenAI call evidence and the controlled r110 upscale crop."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
OUT = PRODUCT / "Images/candidates/openai-transparent-image14"
SOURCE = PRODUCT / "ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
CALLS = [OUT / "call1-strict-edit.png", OUT / "call2-native-regeneration.png"]
R110 = (
    PRODUCT
    / "Images/candidates/bg-assisted-v1/image14/assisted-r110-vitmatte/"
    "image14-assisted-r110-rgba.png"
)
R110_METRICS = R110.parent / "metrics.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def image_record(path: Path) -> dict[str, object]:
    image = Image.open(path)
    record: dict[str, object] = {
        "path": str(path),
        "sha256": sha256(path),
        "mode": image.mode,
        "bands": list(image.getbands()),
        "size": list(image.size),
        "bytes": path.stat().st_size,
        "genuine_alpha": "A" in image.getbands(),
    }
    if "A" in image.getbands():
        alpha = np.asarray(image.getchannel("A"))
        record["alpha"] = {
            "min": int(alpha.min()),
            "max": int(alpha.max()),
            "soft_pct": float(100.0 * np.mean((alpha > 0) & (alpha < 255))),
        }
    return record


def subject_metrics(source: Image.Image, candidate: Image.Image) -> dict[str, float]:
    src = np.asarray(source.convert("RGB"), dtype=np.uint8)
    cand = np.asarray(candidate.convert("RGB").resize(source.size, Image.Resampling.LANCZOS), dtype=np.uint8)
    source_mask = np.min(255 - src, axis=2) > 12
    source_mask = cv2.dilate(source_mask.astype(np.uint8), np.ones((5, 5), np.uint8), iterations=1).astype(bool)
    src_gray = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY)
    cand_gray = cv2.cvtColor(cand, cv2.COLOR_RGB2GRAY)
    src_edges = cv2.Canny(src_gray, 60, 150) > 0
    cand_edges = cv2.Canny(cand_gray, 60, 150) > 0
    src_edges &= source_mask
    cand_edges &= source_mask
    intersection = np.count_nonzero(src_edges & cand_edges)
    union = np.count_nonzero(src_edges | cand_edges)
    return {
        "source_subject_mask_pct": float(100.0 * source_mask.mean()),
        "masked_rgb_mae_0_255": float(
            np.mean(np.abs(src[source_mask].astype(np.float32) - cand[source_mask].astype(np.float32)))
        ),
        "masked_edge_iou": float(intersection / union) if union else 0.0,
    }


def make_call_board(source: Image.Image, calls: list[Image.Image], path: Path) -> None:
    labels = ["authoritative source", "call 1 actual RGB", "call 2 actual RGB"]
    images = [source, *calls]
    tile_h = 836
    tiles = []
    for image in images:
        tile_w = round(image.width * tile_h / image.height)
        tiles.append(image.convert("RGB").resize((tile_w, tile_h), Image.Resampling.LANCZOS))
    label_h = 32
    board = Image.new("RGB", (sum(tile.width for tile in tiles), tile_h + label_h), "white")
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    x = 0
    for label, tile in zip(labels, tiles):
        board.paste(tile, (x, label_h))
        draw.text((x + 6, 10), label, fill="black", font=font)
        x += tile.width
    board.save(path, quality=94)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE)
    calls = [Image.open(path) for path in CALLS]
    make_call_board(source, calls, OUT / "openai-call-comparison-board.jpg")

    crop_box = (80, 80, 320, 320)
    r110 = Image.open(R110).convert("RGBA")
    crop = r110.crop(crop_box)
    crop_path = OUT / "upscale-comparison/r110-control-crop.png"
    crop_path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(crop_path)
    r110_metrics = json.loads(R110_METRICS.read_text(encoding="utf-8"))

    metrics = {
        "source": image_record(SOURCE),
        "calls": [
            {
                **image_record(path),
                "subject_comparison": subject_metrics(source, image),
                "verdict": "FAIL: opaque RGB with baked checkerboard; not native transparency",
            }
            for path, image in zip(CALLS, calls)
        ],
        "actual_openai_image_call_count": 2,
        "call_budget_exhausted": True,
        "wrapper_discovery_defect": (
            "Codex 0.144 writes exec-*.png; scripts/subgen.py only discovers ig_*.png, "
            "so both real images required deterministic session-artifact recovery"
        ),
        "fallback_fixture": {
            **image_record(R110),
            "accepted_art": False,
            "role": "controlled alpha-upscale fixture only",
            "input_rgb_contract_evidence": {
                "metrics_path": str(R110_METRICS),
                "metrics_sha256": sha256(R110_METRICS),
                "representation": r110_metrics["pipeline"]["foreground_rgb"]["representation"],
                "residual_correction": r110_metrics["pipeline"]["foreground_rgb"]["residual_correction"],
            },
            "crop_box_xyxy": list(crop_box),
            "crop": image_record(crop_path),
        },
    }
    (OUT / "openai-call-metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
