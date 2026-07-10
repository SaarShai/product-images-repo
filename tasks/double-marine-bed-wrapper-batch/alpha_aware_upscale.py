#!/usr/bin/env python3
"""Halo-safe x8 upscaling for decontaminated straight-RGBA artwork.

The preferred ``split`` route never sends alpha through the RGB super-resolution
network. ``direct`` records ncnn's native RGBA behavior. ``two-plate`` supports
an opaque-only upscaler by recovering alpha/foreground from matched black and
white plates. All routes keep a strict straight-alpha contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi


REPO = Path(__file__).resolve().parents[2]
DEFAULT_BIN = REPO / "tasks/marine-pod-upscale/tools/realesrgan-full/realesrgan-ncnn-vulkan"
DEFAULT_MODELS = REPO / "tasks/marine-pod-upscale/tools/realesrgan-full/models"
NCNN_SCALE = 4
FINAL_SCALE = 8
LANCZOS = Image.Resampling.LANCZOS
Image.MAX_IMAGE_PIXELS = None


class AlphaUpscaleError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def alpha_stats(alpha: np.ndarray) -> dict[str, float | int]:
    a = np.asarray(alpha, dtype=np.uint8)
    return {
        "min": int(a.min()),
        "max": int(a.max()),
        "unique": int(np.unique(a).size),
        "zero_pct": float(100.0 * np.mean(a == 0)),
        "soft_pct": float(100.0 * np.mean((a > 0) & (a < 255))),
        "opaque_pct": float(100.0 * np.mean(a == 255)),
    }


def compare_alpha_to_split_reference(source: Image.Image, output: Image.Image) -> dict[str, object]:
    expected = np.asarray(
        source.convert("RGBA").getchannel("A").resize(output.size, LANCZOS),
        dtype=np.int16,
    )
    actual = np.asarray(output.convert("RGBA").getchannel("A"), dtype=np.int16)
    difference = np.abs(actual - expected)
    return {
        "reference": "source alpha -> Pillow Lanczos at final dimensions",
        "mae_8bit": float(difference.mean()),
        "max_error_8bit": int(difference.max()),
        "exact_match": bool(np.array_equal(actual, expected)),
    }


def make_review_board(source: Image.Image, max_side: int = 1200) -> Image.Image:
    if max_side <= 0:
        raise AlphaUpscaleError("review max side must be positive")
    rgba = source.convert("RGBA")
    rgba.thumbnail((max_side, max_side), LANCZOS)
    array = np.asarray(rgba, dtype=np.float32)
    rgb = array[:, :, :3]
    alpha = array[:, :, 3:4] / 255.0
    label_height = 26
    tiles = []
    for label, background in (
        ("WHITE", (255, 255, 255)),
        ("GRAY", (128, 128, 128)),
        ("BLACK", (0, 0, 0)),
        ("MAGENTA", (255, 0, 255)),
    ):
        composite = np.clip(
            np.rint(rgb * alpha + np.asarray(background) * (1.0 - alpha)), 0, 255
        ).astype(np.uint8)
        tile = Image.new("RGB", (rgba.width, rgba.height + label_height), "white")
        ImageDraw.Draw(tile).text((5, 7), label, fill="black", font=ImageFont.load_default())
        tile.paste(Image.fromarray(composite), (0, label_height))
        tiles.append(tile)
    board = Image.new(
        "RGB",
        (rgba.width * 2, (rgba.height + label_height) * 2),
        "white",
    )
    for index, tile in enumerate(tiles):
        board.paste(tile, ((index % 2) * rgba.width, (index // 2) * tile.height))
    return board


def reject_final_path(path: Path) -> None:
    parts = {part.lower() for part in path.expanduser().resolve().parts}
    if parts & {"final", "finals"}:
        raise AlphaUpscaleError(f"refusing final output path: {path}")


def validate_request(input_path: Path, output_path: Path, acknowledged: bool) -> None:
    if not acknowledged:
        raise AlphaUpscaleError(
            "input contract not acknowledged; pass --ack-decontaminated-straight-rgb only "
            "after foreground RGB has been decontaminated"
        )
    if not input_path.is_file():
        raise AlphaUpscaleError(f"input does not exist: {input_path}")
    if output_path.suffix.lower() != ".png":
        raise AlphaUpscaleError("output must be PNG")
    reject_final_path(output_path)
    if input_path.expanduser().resolve() == output_path.expanduser().resolve():
        raise AlphaUpscaleError("input and output must differ")
    with Image.open(input_path) as image:
        if "A" not in image.getbands():
            raise AlphaUpscaleError("input must contain a real alpha channel")
        alpha = np.asarray(image.getchannel("A"))
    if int(alpha.min()) != 0 or int(alpha.max()) != 255:
        raise AlphaUpscaleError("input alpha must include both transparent and opaque pixels")
    if not np.any((alpha > 0) & (alpha < 255)):
        raise AlphaUpscaleError("input alpha has no soft edge pixels")


def extend_hidden_rgb(rgb: np.ndarray, alpha: np.ndarray, threshold: int = 1) -> np.ndarray:
    """Nearest-color extension only beneath alpha values below ``threshold``."""
    colors = np.asarray(rgb, dtype=np.uint8)
    a = np.asarray(alpha, dtype=np.uint8)
    if colors.ndim != 3 or colors.shape[2] != 3 or a.shape != colors.shape[:2]:
        raise AlphaUpscaleError("RGB/alpha shape mismatch")
    valid = a >= threshold
    if not np.any(valid):
        raise AlphaUpscaleError("no foreground color is available for extension")
    if np.all(valid):
        return colors.copy()
    indices = ndi.distance_transform_edt(~valid, return_distances=False, return_indices=True)
    extended = colors.copy()
    extended[~valid] = colors[indices[0][~valid], indices[1][~valid]]
    return extended


def composite_rgb(rgba: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    arr = np.asarray(rgba.convert("RGBA"), dtype=np.float32) / 255.0
    alpha = arr[:, :, 3:4]
    bg = np.asarray(background, dtype=np.float32).reshape(1, 1, 3) / 255.0
    comp = arr[:, :, :3] * alpha + bg * (1.0 - alpha)
    return Image.fromarray(np.clip(np.rint(comp * 255.0), 0, 255).astype(np.uint8))


def build_realesrgan_command(
    binary: Path,
    models: Path,
    input_path: Path,
    output_path: Path,
    tile: int = 512,
) -> list[str]:
    return [
        str(binary),
        "-i",
        str(input_path),
        "-o",
        str(output_path),
        "-n",
        "realesrgan-x4plus",
        "-m",
        str(models),
        "-s",
        str(NCNN_SCALE),
        "-t",
        str(tile),
        "-f",
        "png",
    ]


@dataclass
class NcnnUpscaler:
    work_dir: Path
    binary: Path = DEFAULT_BIN
    models: Path = DEFAULT_MODELS
    tile: int = 512
    label: str = "ncnn"
    commands: list[list[str]] = field(default_factory=list)
    counter: int = 0

    def __call__(self, image: Image.Image) -> Image.Image:
        if image.mode not in {"RGB", "RGBA"}:
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.counter += 1
        input_path = self.work_dir / f"{self.counter:02d}-{self.label}-input.png"
        output_path = self.work_dir / f"{self.counter:02d}-{self.label}-x4.png"
        image.save(input_path)
        command = build_realesrgan_command(self.binary, self.models, input_path, output_path, self.tile)
        self.commands.append(command)
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0 or not output_path.is_file():
            raise AlphaUpscaleError(
                f"RealESRGAN failed rc={completed.returncode}: {completed.stderr[-1000:]}"
            )
        result = Image.open(output_path)
        result.load()
        expected = (image.width * NCNN_SCALE, image.height * NCNN_SCALE)
        if result.size != expected:
            raise AlphaUpscaleError(f"unexpected ncnn dimensions {result.size}, expected {expected}")
        return result


Upscaler = Callable[[Image.Image], Image.Image]


def upscale_split(source: Image.Image, upscaler: Upscaler, final_scale: int = FINAL_SCALE) -> Image.Image:
    rgba = source.convert("RGBA")
    rgb = np.asarray(rgba.convert("RGB"), dtype=np.uint8)
    alpha = np.asarray(rgba.getchannel("A"), dtype=np.uint8)
    extended = extend_hidden_rgb(rgb, alpha, threshold=1)
    rgb_x4 = upscaler(Image.fromarray(extended)).convert("RGB")
    final_size = (rgba.width * final_scale, rgba.height * final_scale)
    rgb_final = rgb_x4.resize(final_size, LANCZOS)
    alpha_final = rgba.getchannel("A").resize(final_size, LANCZOS)
    return Image.merge("RGBA", (*rgb_final.split(), alpha_final))


def upscale_direct(source: Image.Image, upscaler: Upscaler, final_scale: int = FINAL_SCALE) -> Image.Image:
    rgba = source.convert("RGBA")
    direct_x4 = upscaler(rgba)
    if "A" not in direct_x4.getbands():
        raise AlphaUpscaleError("direct ncnn route discarded alpha")
    final_size = (rgba.width * final_scale, rgba.height * final_scale)
    return direct_x4.convert("RGBA").resize(final_size, LANCZOS)


def recover_two_plate(
    black: np.ndarray,
    white: np.ndarray,
    alpha_floor: float = 0.02,
) -> tuple[np.ndarray, np.ndarray]:
    """Recover straight RGB/alpha from identical black/white transformed plates."""
    b = np.asarray(black, dtype=np.float32) / 255.0
    w = np.asarray(white, dtype=np.float32) / 255.0
    if b.shape != w.shape or b.ndim != 3 or b.shape[2] != 3:
        raise AlphaUpscaleError("two-plate arrays must be equal HxWx3 RGB")
    transmission = np.clip(np.mean(w - b, axis=2), 0.0, 1.0)
    alpha = np.clip(1.0 - transmission, 0.0, 1.0)
    premul_from_white = w - (1.0 - alpha[:, :, None])
    premul = np.clip(0.5 * (b + premul_from_white), 0.0, alpha[:, :, None])
    straight = np.zeros_like(premul, dtype=np.float32)
    stable = alpha >= alpha_floor
    straight[stable] = premul[stable] / alpha[stable, None]
    straight8 = np.clip(np.rint(straight * 255.0), 0, 255).astype(np.uint8)
    alpha8 = np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8)
    straight8 = extend_hidden_rgb(straight8, alpha8, threshold=max(1, int(round(alpha_floor * 255.0))))
    if not np.isfinite(straight8).all():
        raise AlphaUpscaleError("non-finite recovered foreground")
    return straight8, alpha8


def upscale_two_plate(
    source: Image.Image,
    upscaler: Upscaler,
    final_scale: int = FINAL_SCALE,
    alpha_floor: float = 0.02,
) -> Image.Image:
    rgba = source.convert("RGBA")
    black_x4 = upscaler(composite_rgb(rgba, (0, 0, 0))).convert("RGB")
    white_x4 = upscaler(composite_rgb(rgba, (255, 255, 255))).convert("RGB")
    final_size = (rgba.width * final_scale, rgba.height * final_scale)
    black = np.asarray(black_x4.resize(final_size, LANCZOS), dtype=np.uint8)
    white = np.asarray(white_x4.resize(final_size, LANCZOS), dtype=np.uint8)
    rgb, alpha = recover_two_plate(black, white, alpha_floor=alpha_floor)
    return Image.fromarray(np.dstack([rgb, alpha]))


def output_metrics(
    source_path: Path,
    output_path: Path,
    method: str,
    source_hash_before: str,
    source_hash_after: str,
    commands: list[list[str]],
) -> dict[str, object]:
    with Image.open(source_path) as source, Image.open(output_path) as output:
        out_alpha = np.asarray(output.getchannel("A"))
        alpha_routes = {
            "split": "source alpha -> Pillow Lanczos x8, independent of RGB super-resolution",
            "direct": "ncnn internal RGBA alpha handling x4 -> Pillow Lanczos x2",
            "two-plate": "recovered after matched black/white ncnn x4 + Pillow Lanczos x2 plates",
        }
        return {
            "method": method,
            "straight_alpha": True,
            "input_rgb_contract": "caller acknowledged decontaminated foreground RGB",
            "alpha_route": alpha_routes[method],
            "source": str(source_path),
            "source_sha256_before": source_hash_before,
            "source_sha256_after": source_hash_after,
            "source_unchanged": source_hash_before == source_hash_after,
            "source_size": list(source.size),
            "output": str(output_path),
            "output_sha256": sha256(output_path),
            "output_mode": output.mode,
            "output_size": list(output.size),
            "expected_size": [source.width * FINAL_SCALE, source.height * FINAL_SCALE],
            "alpha": alpha_stats(out_alpha),
            "alpha_vs_split_reference": compare_alpha_to_split_reference(source, output),
            "hidden_rgb_finite_bounded": True,
            "commands": commands,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--method", choices=("split", "direct", "two-plate"), default="split")
    parser.add_argument("--scale", type=int, choices=(FINAL_SCALE,), default=FINAL_SCALE)
    parser.add_argument("--realesrgan-bin", type=Path, default=DEFAULT_BIN)
    parser.add_argument("--models", type=Path, default=DEFAULT_MODELS)
    parser.add_argument("--tile", type=int, default=512)
    parser.add_argument("--alpha-floor", type=float, default=0.02)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--metrics", type=Path)
    parser.add_argument("--review-board", type=Path)
    parser.add_argument("--review-max-side", type=int, default=1200)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--ack-decontaminated-straight-rgb", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    output_path = args.output.expanduser().resolve()
    validate_request(input_path, output_path, args.ack_decontaminated_straight_rgb)
    if output_path.exists() and not args.overwrite:
        raise AlphaUpscaleError(f"output already exists: {output_path}; pass --overwrite")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir = (args.work_dir or output_path.parent / f"{output_path.stem}-work").resolve()
    reject_final_path(work_dir)
    source_hash_before = sha256(input_path)
    with Image.open(input_path) as opened:
        source = opened.convert("RGBA")
    runner = NcnnUpscaler(
        work_dir=work_dir,
        binary=args.realesrgan_bin.expanduser().resolve(),
        models=args.models.expanduser().resolve(),
        tile=args.tile,
        label=args.method,
    )
    if args.method == "split":
        result = upscale_split(source, runner, final_scale=args.scale)
    elif args.method == "direct":
        result = upscale_direct(source, runner, final_scale=args.scale)
    else:
        result = upscale_two_plate(source, runner, final_scale=args.scale, alpha_floor=args.alpha_floor)
    if result.mode != "RGBA" or result.size != (source.width * args.scale, source.height * args.scale):
        raise AlphaUpscaleError("output contract failed before save")
    output_alpha = np.asarray(result.getchannel("A"))
    if not np.any((output_alpha > 0) & (output_alpha < 255)):
        raise AlphaUpscaleError("output alpha is not soft/nondegenerate")
    result.save(output_path)
    del result, output_alpha
    source_hash_after = sha256(input_path)
    metrics = output_metrics(
        input_path,
        output_path,
        args.method,
        source_hash_before,
        source_hash_after,
        runner.commands,
    )
    if not metrics["source_unchanged"]:
        raise AlphaUpscaleError("source changed during upscale")
    if args.review_board is not None:
        review_path = args.review_board.expanduser().resolve()
        reject_final_path(review_path)
        if review_path == output_path:
            raise AlphaUpscaleError("review board and RGBA output must differ")
        review_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(output_path) as output:
            make_review_board(output, max_side=args.review_max_side).save(review_path)
        metrics["review_board"] = {
            "path": str(review_path),
            "sha256": sha256(review_path),
            "backgrounds": ["white", "gray", "black", "magenta"],
        }
    metrics_path = (args.metrics or output_path.with_suffix(".metrics.json")).expanduser().resolve()
    reject_final_path(metrics_path)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
