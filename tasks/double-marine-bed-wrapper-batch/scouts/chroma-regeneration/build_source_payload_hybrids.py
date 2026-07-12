#!/usr/bin/env python3
"""Use green regenerations only as alpha oracles; preserve original RGB payload."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pymatting import estimate_foreground_ml
from scipy.ndimage import distance_transform_edt

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("chroma_process", HERE / "process_candidates.py")
PROCESS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PROCESS)

OUT = PROCESS.OUT
SOURCE = PROCESS.SOURCE
ELIGIBLE_IDS = ("flux2-a", "nano-a")
KEY = np.array([0.0, 255.0, 0.0], dtype=np.float32)
SURE_BACKGROUND_DISTANCE = 30.0
SURE_FOREGROUND_DISTANCE = 180.0
VERIFIED_BLANK_SOURCE_BORDER_PX = 8


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def alpha_from_green_oracle(candidate_rgb: np.ndarray) -> tuple[np.ndarray, dict]:
    colors = candidate_rgb.astype(np.float32)
    distance = np.linalg.norm(colors - KEY, axis=2)
    sure_background = distance <= SURE_BACKGROUND_DISTANCE
    sure_foreground = distance >= SURE_FOREGROUND_DISTANCE
    unknown = ~(sure_background | sure_foreground)
    _, indices = distance_transform_edt(~sure_foreground, return_indices=True)
    nearest_foreground = colors[tuple(indices)]
    foreground_vector = nearest_foreground - KEY
    observed_vector = colors - KEY
    alpha = np.sum(observed_vector * foreground_vector, axis=2) / np.maximum(
        1e-6, np.sum(foreground_vector * foreground_vector, axis=2)
    )
    alpha = np.clip(alpha, 0.0, 1.0)
    alpha[sure_background] = 0.0
    alpha[sure_foreground] = 1.0
    return alpha, {
        "method": "local_nearest_sure_foreground_projection_from_green_plate",
        "luma_used": False,
        "sure_background_distance_rgb": SURE_BACKGROUND_DISTANCE,
        "sure_foreground_distance_rgb": SURE_FOREGROUND_DISTANCE,
        "sure_background_fraction_native": float(sure_background.mean()),
        "sure_foreground_fraction_native": float(sure_foreground.mean()),
        "unknown_fraction_native": float(unknown.mean()),
        "nearest_foreground_is_color_donor_only": True,
    }


def composite(rgb: np.ndarray, alpha: np.ndarray, background: tuple[int, int, int]) -> np.ndarray:
    value = rgb * alpha[..., None] + (np.array(background, dtype=np.float64) / 255.0) * (1.0 - alpha[..., None])
    return np.clip(np.round(value * 255.0), 0, 255).astype(np.uint8)


def full_board(source: Image.Image, raw: Image.Image, reviews: dict[str, Image.Image], path: Path, title: str) -> None:
    panels = [("original payload", source), ("green alpha oracle", raw)] + [(name, reviews[name]) for name in ("gray", "black", "magenta", "white")]
    tile = (270, 480)
    label_h = 38
    board = Image.new("RGB", (tile[0] * len(panels), tile[1] + label_h), "#181818")
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    for column, (name, image) in enumerate(panels):
        board.paste(PROCESS.fit(image, tile), (column * tile[0], label_h))
        draw.text((column * tile[0] + 5, 5), name, fill="white", font=font)
    draw.text((5, 21), title, fill="#cccccc", font=font)
    board.save(path, quality=94)


def crop_boards(source_rgb: np.ndarray, alpha: np.ndarray, recovered_rgb: np.ndarray, directory: Path) -> dict:
    panels = {
        "source": source_rgb,
        "alpha": np.repeat(np.round(alpha[..., None] * 255.0).astype(np.uint8), 3, axis=2),
        "gray": composite(recovered_rgb, alpha, (128, 128, 128)),
        "black": composite(recovered_rgb, alpha, (0, 0, 0)),
        "magenta": composite(recovered_rgb, alpha, (255, 0, 255)),
        "white": composite(recovered_rgb, alpha, (255, 255, 255)),
    }
    font = ImageFont.load_default()
    records = {}
    for name, spec in PROCESS.ROIS.items():
        box = PROCESS.roi_box(spec["center"], spec["size"], (source_rgb.shape[1], source_rgb.shape[0]))
        width, height = spec["size"]
        scale = 2
        label_h = 24
        board = Image.new("RGB", (width * scale * len(panels), height * scale + label_h), "#202020")
        draw = ImageDraw.Draw(board)
        for column, (panel_name, array) in enumerate(panels.items()):
            crop = Image.fromarray(array).crop(box).resize((width * scale, height * scale), Image.Resampling.NEAREST)
            board.paste(crop, (column * width * scale, label_h))
            draw.text((column * width * scale + 3, 6), panel_name, fill="white", font=font)
        board.save(directory / f"crop-{name}.png")
        records[name] = {"source_native_box": list(box), "scale_for_board": scale}
    return records


def build(record: dict, source_rgb_u8: np.ndarray, source_proxy: np.ndarray) -> dict:
    candidate_id = record["id"]
    raw_path = Path(record["output"]["path"])
    raw_image = Image.open(raw_path).convert("RGB")
    candidate_rgb = np.asarray(raw_image, dtype=np.uint8)
    alpha_native, oracle_metrics = alpha_from_green_oracle(candidate_rgb)
    candidate_white = PROCESS.composite(candidate_rgb, alpha_native, (255, 255, 255))
    _, alpha_registered, registration = PROCESS.register_analysis(
        source_rgb_u8, candidate_white, alpha_native, candidate_rgb
    )
    alpha_registered = cv2.medianBlur(
        np.round(alpha_registered * 65535.0).astype(np.uint16), 3
    ).astype(np.float64) / 65535.0
    alpha_registered = np.clip(alpha_registered, 0.0, 1.0)
    border = VERIFIED_BLANK_SOURCE_BORDER_PX
    alpha_registered[:border, :] = 0.0
    alpha_registered[-border:, :] = 0.0
    alpha_registered[:, :border] = 0.0
    alpha_registered[:, -border:] = 0.0

    source_float = source_rgb_u8.astype(np.float64) / 255.0
    estimated_foreground = estimate_foreground_ml(source_float, alpha_registered)
    recovered_foreground = estimated_foreground.copy()
    exact_interior = alpha_registered >= (65534.0 / 65535.0)
    recovered_foreground[exact_interior] = source_float[exact_interior]

    directory = OUT / candidate_id / "source-payload-hybrid"
    directory.mkdir(exist_ok=True)
    alpha_u16 = np.round(alpha_registered * 65535.0).astype(np.uint16)
    Image.fromarray(alpha_u16).save(directory / "alpha-16bit.png")
    rgba = np.dstack([
        np.clip(np.round(recovered_foreground * 255.0), 0, 255).astype(np.uint8),
        np.clip(np.round(alpha_registered * 255.0), 0, 255).astype(np.uint8),
    ])
    Image.fromarray(rgba).save(directory / "source-payload-rgba.png")

    backgrounds = {"gray": (128, 128, 128), "black": (0, 0, 0), "magenta": (255, 0, 255), "white": (255, 255, 255)}
    reviews = {}
    for name, background in backgrounds.items():
        review = Image.fromarray(composite(recovered_foreground, alpha_registered, background))
        review.save(directory / f"on-{name}.png")
        reviews[name] = review
    full_board(Image.fromarray(source_rgb_u8), raw_image, reviews, directory / "full-board.jpg", f"{candidate_id}: regenerated alpha + original RGB payload")
    roi_records = crop_boards(source_rgb_u8, alpha_registered, recovered_foreground, directory)

    interior_diff = np.abs(
        np.clip(np.round(recovered_foreground * 255.0), 0, 255).astype(np.int16)
        - source_rgb_u8.astype(np.int16)
    ).max(axis=2)
    collision_proxy = float(((alpha_registered <= 0.05) & source_proxy).sum() / max(1, source_proxy.sum()))
    paper_proxy = ~source_proxy
    opaque_paper_proxy = float(((alpha_registered >= 0.95) & paper_proxy).sum() / max(1, paper_proxy.sum()))
    metrics = {
        "candidate_id": candidate_id,
        "architecture": "registered_green_alpha_oracle_plus_original_source_rgb_payload_plus_white_matte_foreground_recovery",
        "candidate_rgb_used_in_final_payload": False,
        "original_source_rgb_is_payload": True,
        "alpha_oracle": oracle_metrics,
        "registration": registration,
        "alpha_registered": {
            "fully_transparent_fraction": float((alpha_registered <= 0.0).mean()),
            "soft_fraction": float(((alpha_registered > 0.0) & (alpha_registered < 1.0)).mean()),
            "fully_opaque_fraction": float((alpha_registered >= 1.0).mean()),
        },
        "payload": {
            "source_sha256": sha256(SOURCE),
            "foreground_recovery": "pymatting.estimate_foreground_ml against original white matte",
            "verified_blank_source_border_forced_transparent_px": VERIFIED_BLANK_SOURCE_BORDER_PX,
            "exact_source_rgb_for_fully_opaque_pixels": True,
            "fully_opaque_pixel_count": int(exact_interior.sum()),
            "maximum_rgb_delta_on_exact_interior": int(interior_diff[exact_interior].max(initial=0)),
        },
        "diagnostic_proxies": {
            "source_nonpaper_deleted_alpha_le_0_05_fraction": collision_proxy,
            "source_paper_proxy_opaque_alpha_ge_0_95_fraction": opaque_paper_proxy,
            "proxy_warning": "CIELAB source proxies are diagnostics, not semantic ground truth",
        },
        "roi_records": roi_records,
        "artifacts": {
            "rgba": {"path": str(directory / "source-payload-rgba.png"), "sha256": sha256(directory / "source-payload-rgba.png")},
            "alpha_16bit": {"path": str(directory / "alpha-16bit.png"), "sha256": sha256(directory / "alpha-16bit.png")},
            "full_board": {"path": str(directory / "full-board.jpg"), "sha256": sha256(directory / "full-board.jpg")},
        },
        "requires_separate_vision_verdict": True,
    }
    (directory / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    return metrics


def comparison(metrics: list[dict]) -> None:
    tile = (270, 480)
    label_h = 34
    board = Image.new("RGB", (tile[0] * 3, (tile[1] + label_h) * len(metrics)), "#181818")
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    source = Image.open(SOURCE).convert("RGB")
    for row, metric in enumerate(metrics):
        candidate_id = metric["candidate_id"]
        directory = OUT / candidate_id / "source-payload-hybrid"
        panels = (
            ("original", source),
            ("hybrid black", Image.open(directory / "on-black.png").convert("RGB")),
            ("hybrid magenta", Image.open(directory / "on-magenta.png").convert("RGB")),
        )
        for column, (name, image) in enumerate(panels):
            y = row * (tile[1] + label_h)
            board.paste(PROCESS.fit(image, tile), (column * tile[0], y + label_h))
            draw.text((column * tile[0] + 5, y + 6), f"{candidate_id} | {name}", fill="white", font=font)
    board.save(OUT / "source-payload-hybrid-comparison.png")


def main() -> None:
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    source_rgb = np.asarray(Image.open(SOURCE).convert("RGB"), dtype=np.uint8)
    source_proxy = PROCESS.source_subject_proxy(source_rgb)
    records = [record for record in manifest["new_candidates"] if record["id"] in ELIGIBLE_IDS]
    metrics = [build(record, source_rgb, source_proxy) for record in records]
    comparison(metrics)
    manifest["source_payload_hybrid"] = {
        "status": "probe_complete_requires_parent_vision",
        "eligible_ids": list(ELIGIBLE_IDS),
        "architecture": "green regeneration supplies registered alpha only; original source supplies RGB; PyMatting removes white matte",
        "comparison_board": str(OUT / "source-payload-hybrid-comparison.png"),
        "comparison_board_sha256": sha256(OUT / "source-payload-hybrid-comparison.png"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"HYBRID_OK candidates={len(metrics)} ids={[metric['candidate_id'] for metric in metrics]}")


if __name__ == "__main__":
    main()
