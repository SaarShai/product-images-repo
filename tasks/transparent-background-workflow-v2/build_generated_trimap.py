#!/usr/bin/env python3
"""Build a conservative trimap for generated art on a nearly uniform key color.

Only nearly neutral, key-colored pixels connected to the image border are
labeled sure background.  Strongly chromatic or key-distant pixels are sure
foreground.  Everything else—including enclosed white highlights and pale
off-white art—remains unknown for a matting backend to solve.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image
from scipy import ndimage as ndi


Image.MAX_IMAGE_PIXELS = None

SURE_BG = np.uint8(0)
UNKNOWN = np.uint8(128)
SURE_FG = np.uint8(255)


@dataclass(frozen=True)
class TrimapConfig:
    key_distance_8bit: float = 18.0
    neutral_chroma_8bit: int = 8
    foreground_distance_8bit: float = 55.0
    foreground_chroma_8bit: int = 24
    chromatic_min_distance_8bit: float = 20.0
    connectivity: int = 4

    def validate(self) -> None:
        if self.key_distance_8bit <= 0:
            raise ValueError("key distance must be positive")
        if not 0 <= self.neutral_chroma_8bit <= 255:
            raise ValueError("neutral chroma must be in [0, 255]")
        if self.foreground_distance_8bit <= self.key_distance_8bit:
            raise ValueError("foreground distance must exceed key distance")
        if not 0 <= self.foreground_chroma_8bit <= 255:
            raise ValueError("foreground chroma must be in [0, 255]")
        if self.chromatic_min_distance_8bit < self.key_distance_8bit:
            raise ValueError("chromatic minimum distance must not be below key distance")
        if self.connectivity not in {4, 8}:
            raise ValueError("connectivity must be 4 or 8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def estimate_key_rgb(rgb: np.ndarray) -> np.ndarray:
    """Return the per-channel border median as a robust key-color estimate."""
    image = np.asarray(rgb)
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("rgb must be an 8-bit HxWx3 array")
    border = np.concatenate((image[0], image[-1], image[:, 0], image[:, -1]), axis=0)
    return np.median(border, axis=0).astype(np.float32)


def _border_connected(mask: np.ndarray, connectivity: int) -> np.ndarray:
    structure = ndi.generate_binary_structure(2, 1 if connectivity == 4 else 2)
    seeds = np.zeros(mask.shape, dtype=bool)
    seeds[0, :] = mask[0, :]
    seeds[-1, :] = mask[-1, :]
    seeds[:, 0] = mask[:, 0]
    seeds[:, -1] = mask[:, -1]
    return ndi.binary_propagation(seeds, structure=structure, mask=mask)


def build_trimap_array(
    rgb: np.ndarray,
    config: TrimapConfig = TrimapConfig(),
) -> tuple[np.ndarray, dict[str, Any]]:
    """Return a 0/128/255 trimap and auditable class-count metrics."""
    config.validate()
    image = np.asarray(rgb)
    if image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ValueError("rgb must be an 8-bit HxWx3 array")

    key = estimate_key_rgb(image)
    image_f = image.astype(np.float32)
    distance = np.linalg.norm(image_f - key[None, None, :], axis=2)
    chroma = image.max(axis=2).astype(np.int16) - image.min(axis=2).astype(np.int16)

    near_neutral_key = (
        (distance <= config.key_distance_8bit)
        & (chroma <= config.neutral_chroma_8bit)
    )
    sure_bg = _border_connected(near_neutral_key, config.connectivity)

    chromatic_subject = (
        (chroma >= config.foreground_chroma_8bit)
        & (distance >= config.chromatic_min_distance_8bit)
    )
    distant_subject = distance >= config.foreground_distance_8bit
    sure_fg = (chromatic_subject | distant_subject) & ~sure_bg

    trimap = np.full(image.shape[:2], UNKNOWN, dtype=np.uint8)
    trimap[sure_bg] = SURE_BG
    trimap[sure_fg] = SURE_FG

    counts = {
        "sure_background": int(np.count_nonzero(trimap == SURE_BG)),
        "unknown": int(np.count_nonzero(trimap == UNKNOWN)),
        "sure_foreground": int(np.count_nonzero(trimap == SURE_FG)),
    }
    metrics: dict[str, Any] = {
        "schema": "generated-key-trimap/v1",
        "status": "proposal-only-unapproved",
        "size_wh": [int(image.shape[1]), int(image.shape[0])],
        "key_rgb": [float(value) for value in key],
        "counts": counts,
        "fractions": {
            name: count / float(trimap.size) for name, count in counts.items()
        },
        "config": asdict(config),
    }
    return trimap, metrics


def save_proposal(path: Path, trimap: np.ndarray, mode: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "L":
        Image.fromarray(trimap).save(path)
        return
    if mode == "RGBA":
        rgba = np.full((*trimap.shape, 4), 255, dtype=np.uint8)
        rgba[:, :, 3] = trimap
        Image.fromarray(rgba).save(path)
        return
    raise ValueError("mode must be L or RGBA")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--mode", choices=("L", "RGBA"), default="L")
    parser.add_argument("--key-distance", type=float, default=18.0)
    parser.add_argument("--neutral-chroma", type=int, default=8)
    parser.add_argument("--foreground-distance", type=float, default=55.0)
    parser.add_argument("--foreground-chroma", type=int, default=24)
    parser.add_argument("--chromatic-min-distance", type=float, default=20.0)
    parser.add_argument("--connectivity", type=int, choices=(4, 8), default=4)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for path in (args.output, args.metrics):
        if path.exists() and not args.overwrite:
            raise FileExistsError(f"output exists; pass --overwrite: {path}")
    if args.output.resolve() == args.metrics.resolve():
        raise ValueError("proposal and metrics outputs must differ")

    source_path = args.source.expanduser().resolve()
    with Image.open(source_path) as source_image:
        rgb = np.asarray(source_image.convert("RGB"), dtype=np.uint8)
    config = TrimapConfig(
        key_distance_8bit=args.key_distance,
        neutral_chroma_8bit=args.neutral_chroma,
        foreground_distance_8bit=args.foreground_distance,
        foreground_chroma_8bit=args.foreground_chroma,
        chromatic_min_distance_8bit=args.chromatic_min_distance,
        connectivity=args.connectivity,
    )
    trimap, metrics = build_trimap_array(rgb, config)
    save_proposal(args.output, trimap, args.mode)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    metrics["source"] = {"path": str(source_path), "sha256": sha256_file(source_path)}
    metrics["proposal"] = {
        "path": str(args.output.expanduser().resolve()),
        "sha256": sha256_file(args.output),
        "mode": args.mode,
        "semantics": {"0": "sure-background", "128": "unknown", "255": "sure-foreground"},
    }
    args.metrics.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
