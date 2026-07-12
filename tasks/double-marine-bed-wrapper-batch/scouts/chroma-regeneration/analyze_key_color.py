#!/usr/bin/env python3
"""Rank high-saturation chroma candidates against source non-paper colors."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.color import deltaE_ciede2000, rgb2lab

CANDIDATES = {
    "pure-green": "#00FF00",
    "pure-cyan": "#00FFFF",
    "pure-blue": "#0000FF",
    "pure-red": "#FF0000",
    "pure-magenta": "#FF00FF",
    "pure-yellow": "#FFFF00",
}


def rgb_from_hex(value: str) -> np.ndarray:
    return np.array([int(value[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.uint8)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    source = np.asarray(Image.open(args.source).convert("RGB"), dtype=np.float32) / 255.0
    lab = rgb2lab(source)
    lightness = lab[..., 0]
    chroma = np.hypot(lab[..., 1], lab[..., 2])
    visual_nonpaper = (chroma >= 7.0) | (lightness <= 92.0)
    samples = lab[visual_nonpaper]

    records = []
    for name, value in CANDIDATES.items():
        rgb = rgb_from_hex(value)
        key_lab = rgb2lab((rgb.astype(np.float32) / 255.0)[None, None])[0, 0]
        distances = deltaE_ciede2000(samples, np.broadcast_to(key_lab, samples.shape))
        records.append({
            "name": name,
            "hex": value,
            "rgb": rgb.tolist(),
            "minimum_delta_e_2000": float(distances.min()),
            "q_0_01_percent_delta_e_2000": float(np.quantile(distances, 0.0001)),
            "q_0_1_percent_delta_e_2000": float(np.quantile(distances, 0.001)),
            "q_1_percent_delta_e_2000": float(np.quantile(distances, 0.01)),
            "mean_delta_e_2000": float(distances.mean()),
            "collision_fraction_delta_e_lt_10": float((distances < 10).mean()),
            "collision_fraction_delta_e_lt_15": float((distances < 15).mean()),
        })
    records.sort(key=lambda record: (
        record["q_0_1_percent_delta_e_2000"],
        record["minimum_delta_e_2000"],
    ), reverse=True)
    winner = records[0]
    result = {
        "source_path": str(args.source),
        "source_sha256": sha256(args.source),
        "source_size": [source.shape[1], source.shape[0]],
        "visual_nonpaper_proxy": "CIELAB chroma >= 7 or L* <= 92",
        "visual_nonpaper_pixel_count": int(visual_nonpaper.sum()),
        "visual_nonpaper_fraction": float(visual_nonpaper.mean()),
        "ranking_rule": "maximize q_0_1_percent_delta_e_2000, break ties by minimum_delta_e_2000",
        "selected": winner,
        "candidates": records,
    }
    (args.output / "key-color-analysis.json").write_text(json.dumps(result, indent=2) + "\n")

    font = ImageFont.load_default()
    width, row_h = 960, 72
    board = Image.new("RGB", (width, 58 + row_h * len(records)), "white")
    draw = ImageDraw.Draw(board)
    draw.text((12, 10), "Image14 key-color separation from visually non-paper source pixels", fill="black", font=font)
    draw.text((12, 30), "rank: robust 0.1% CIEDE2000 distance; larger is safer", fill="#333333", font=font)
    for row, record in enumerate(records):
        y = 58 + row * row_h
        color = tuple(record["rgb"])
        draw.rectangle((12, y + 8, 72, y + 60), fill=color, outline="black")
        draw.text((88, y + 8), f"{row + 1}. {record['name']} {record['hex']}", fill="black", font=font)
        draw.text(
            (88, y + 28),
            "min={:.2f}  q0.1%={:.2f}  q1%={:.2f}  collision<15={:.6f}".format(
                record["minimum_delta_e_2000"],
                record["q_0_1_percent_delta_e_2000"],
                record["q_1_percent_delta_e_2000"],
                record["collision_fraction_delta_e_lt_15"],
            ),
            fill="#222222",
            font=font,
        )
    board.save(args.output / "key-color-analysis-board.png")
    print(
        f"KEY_COLOR_OK selected={winner['hex']} min_delta_e={winner['minimum_delta_e_2000']:.4f} "
        f"q0.1={winner['q_0_1_percent_delta_e_2000']:.4f}"
    )


if __name__ == "__main__":
    main()
