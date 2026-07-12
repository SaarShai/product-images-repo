#!/usr/bin/env python3
"""Measure and render direct/split/two-plate alpha-upscale comparisons."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/"
    "openai-transparent-image14"
)
SYNTH = ROOT / "synthetic-comparison"
REAL = ROOT / "upscale-comparison"
BACKGROUNDS = {
    "white": (255, 255, 255),
    "gray": (128, 128, 128),
    "black": (0, 0, 0),
    "magenta": (255, 0, 255),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def composite(image: Image.Image, background: tuple[int, int, int]) -> np.ndarray:
    arr = np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0
    alpha = arr[:, :, 3:4]
    bg = np.asarray(background, dtype=np.float32).reshape(1, 1, 3) / 255.0
    return np.clip(np.rint((arr[:, :, :3] * alpha + bg * (1 - alpha)) * 255), 0, 255).astype(np.uint8)


def image_record(path: Path) -> dict[str, object]:
    image = Image.open(path).convert("RGBA")
    alpha = np.asarray(image.getchannel("A"))
    rgb = np.asarray(image.convert("RGB"))
    return {
        "path": str(path),
        "sha256": sha256(path),
        "mode": "RGBA",
        "size": list(image.size),
        "alpha": {
            "min": int(alpha.min()),
            "max": int(alpha.max()),
            "soft_pct": float(100.0 * np.mean((alpha > 0) & (alpha < 255))),
            "zero_pct": float(100.0 * np.mean(alpha == 0)),
            "opaque_pct": float(100.0 * np.mean(alpha == 255)),
        },
        "rgb_finite": bool(np.isfinite(rgb).all()),
        "rgb_bounds": [int(rgb.min()), int(rgb.max())],
    }


def comparison_metrics(reference: Image.Image, candidate: Image.Image) -> dict[str, object]:
    ref = reference.convert("RGBA")
    cand = candidate.convert("RGBA")
    if ref.size != cand.size:
        raise ValueError(f"size mismatch {ref.size} != {cand.size}")
    ref_alpha = np.asarray(ref.getchannel("A"), dtype=np.float32)
    cand_alpha = np.asarray(cand.getchannel("A"), dtype=np.float32)
    soft = (ref_alpha > 0) & (ref_alpha < 255)
    zero = ref_alpha == 0
    opaque = ref_alpha == 255
    delta = np.abs(ref_alpha - cand_alpha)
    output: dict[str, object] = {
        "alpha_mae_0_255": float(delta.mean()),
        "alpha_mae_normalized": float(delta.mean() / 255.0),
        "alpha_max_abs_0_255": float(delta.max()),
        "candidate_alpha_mean_where_reference_zero": float(cand_alpha[zero].mean()) if zero.any() else None,
        "candidate_alpha_deficit_where_reference_opaque": float((255 - cand_alpha[opaque]).mean()) if opaque.any() else None,
        "reference_soft_pixel_count": int(soft.sum()),
        "composite_mae_0_255": {},
        "soft_edge_composite_mae_0_255": {},
    }
    for name, background in BACKGROUNDS.items():
        ref_comp = composite(ref, background).astype(np.float32)
        cand_comp = composite(cand, background).astype(np.float32)
        error = np.abs(ref_comp - cand_comp)
        output["composite_mae_0_255"][name] = float(error.mean())
        output["soft_edge_composite_mae_0_255"][name] = float(error[soft].mean()) if soft.any() else None
    return output


def two_plate_recomposition_metrics(
    recovered: Image.Image,
    black_plate_x4: Path,
    white_plate_x4: Path,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for name, path, background in (
        ("black", black_plate_x4, (0, 0, 0)),
        ("white", white_plate_x4, (255, 255, 255)),
    ):
        transformed = np.asarray(
            Image.open(path).convert("RGB").resize(recovered.size, Image.Resampling.LANCZOS),
            dtype=np.float32,
        )
        recomposed = composite(recovered, background).astype(np.float32)
        result[f"{name}_mae_0_255"] = float(np.mean(np.abs(transformed - recomposed)))
        result[f"{name}_max_abs_0_255"] = float(np.max(np.abs(transformed - recomposed)))
    return result


def make_board(
    path: Path,
    source: Image.Image,
    methods: list[tuple[str, Image.Image]],
    tile_size: int,
) -> None:
    rows = [("source Lanczos", source.resize(methods[0][1].size, Image.Resampling.LANCZOS)), *methods]
    label_h = 28
    board = Image.new(
        "RGB",
        (tile_size * len(BACKGROUNDS), (tile_size + label_h) * len(rows)),
        "white",
    )
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    for row, (method_name, image) in enumerate(rows):
        y0 = row * (tile_size + label_h)
        for col, (bg_name, bg) in enumerate(BACKGROUNDS.items()):
            comp = Image.fromarray(composite(image, bg), "RGB").resize(
                (tile_size, tile_size), Image.Resampling.LANCZOS
            )
            board.paste(comp, (col * tile_size, y0 + label_h))
            draw.text((col * tile_size + 5, y0 + 8), f"{method_name} / {bg_name}", fill="black", font=font)
    board.save(path)


def make_alpha_board(path: Path, methods: list[tuple[str, Image.Image]], tile_size: int) -> None:
    label_h = 28
    board = Image.new("L", (tile_size * len(methods), tile_size + label_h), 255)
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    for col, (name, image) in enumerate(methods):
        alpha = image.getchannel("A").resize((tile_size, tile_size), Image.Resampling.LANCZOS)
        board.paste(alpha, (col * tile_size, label_h))
        draw.text((col * tile_size + 5, 8), name, fill=0, font=font)
    board.save(path)


def main() -> None:
    # The direct synthetic x4 is the one authorized RGBA probe; x2 here is only
    # deterministic Lanczos completion to the common x8 comparison size.
    direct_synth_path = SYNTH / "synthetic-direct-x8.png"
    Image.open(ROOT / "ncnn-rgba-probe/synthetic-rgba-64-ncnn-x4.png").convert("RGBA").resize(
        (512, 512), Image.Resampling.LANCZOS
    ).save(direct_synth_path)

    synth_source = Image.open(ROOT / "ncnn-rgba-probe/synthetic-rgba-64.png").convert("RGBA")
    synth_split = Image.open(SYNTH / "synthetic-split-x8.png").convert("RGBA")
    synth_direct = Image.open(direct_synth_path).convert("RGBA")
    synth_two = Image.open(SYNTH / "synthetic-two-plate-x8.png").convert("RGBA")
    make_board(
        SYNTH / "direct-vs-split-vs-two-plate-board.png",
        synth_source,
        [("split", synth_split), ("direct", synth_direct), ("two-plate", synth_two)],
        tile_size=256,
    )
    make_alpha_board(
        SYNTH / "alpha-board.png",
        [("split oracle", synth_split), ("direct", synth_direct), ("two-plate", synth_two)],
        tile_size=256,
    )

    real_source = Image.open(REAL / "r110-control-crop.png").convert("RGBA")
    real_split = Image.open(REAL / "r110-crop-split-x8.png").convert("RGBA")
    real_direct = Image.open(REAL / "r110-crop-direct-x8.png").convert("RGBA")
    real_two = Image.open(REAL / "r110-crop-two-plate-x8.png").convert("RGBA")
    make_board(
        REAL / "direct-vs-split-vs-two-plate-board.png",
        real_source,
        [("split", real_split), ("direct", real_direct), ("two-plate", real_two)],
        tile_size=360,
    )
    make_alpha_board(
        REAL / "alpha-board.png",
        [("split reference", real_split), ("direct", real_direct), ("two-plate", real_two)],
        tile_size=360,
    )

    metrics = {
        "claim_boundary": (
            "Synthetic split alpha is the known-alpha oracle. Real r110 split is only the "
            "controlled route reference; r110 is not accepted artwork."
        ),
        "synthetic_known_alpha": {
            "source": image_record(ROOT / "ncnn-rgba-probe/synthetic-rgba-64.png"),
            "split_oracle": image_record(SYNTH / "synthetic-split-x8.png"),
            "direct": {
                **image_record(direct_synth_path),
                "vs_split_oracle": comparison_metrics(synth_split, synth_direct),
            },
            "two_plate": {
                **image_record(SYNTH / "synthetic-two-plate-x8.png"),
                "vs_split_oracle": comparison_metrics(synth_split, synth_two),
                "white_black_recomposition": two_plate_recomposition_metrics(
                    synth_two,
                    SYNTH / "work-two-plate/01-two-plate-x4.png",
                    SYNTH / "work-two-plate/02-two-plate-x4.png",
                ),
            },
        },
        "real_r110_control_crop": {
            "source": image_record(REAL / "r110-control-crop.png"),
            "accepted_art": False,
            "split_reference": image_record(REAL / "r110-crop-split-x8.png"),
            "direct": {
                **image_record(REAL / "r110-crop-direct-x8.png"),
                "vs_split_reference": comparison_metrics(real_split, real_direct),
            },
            "two_plate": {
                **image_record(REAL / "r110-crop-two-plate-x8.png"),
                "vs_split_reference": comparison_metrics(real_split, real_two),
                "white_black_recomposition": two_plate_recomposition_metrics(
                    real_two,
                    REAL / "work-two-plate/01-two-plate-x4.png",
                    REAL / "work-two-plate/02-two-plate-x4.png",
                ),
            },
        },
        "route_conclusion": (
            "split is preferred: exact independently resampled known alpha and one SR call; "
            "direct delegates alpha to undocumented ncnn resampling; two-plate is mathematically "
            "recoverable only for a linear/equivariant upscaler and accumulates nonlinear SR error"
        ),
    }
    (ROOT / "upscale-comparison-metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
