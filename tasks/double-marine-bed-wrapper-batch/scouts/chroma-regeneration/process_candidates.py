#!/usr/bin/env python3
"""Deterministically key, despill, register, score, and board matrix outputs."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.color import rgb2lab
from skimage.metrics import structural_similarity

SOURCE = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
)
OUT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/chroma-regeneration/image14"
)
RADIUS_TRANSPARENT = 30.0
RADIUS_OPAQUE = 115.0
DESPILL_CAP = 64.0
ROIS = {
    "cutout_01": {"center": (286, 1001), "size": (96, 96)},
    "cutout_02": {"center": (567, 889), "size": (96, 96)},
    "fringe_00": {"center": (880, 1072), "size": (96, 96)},
    "outer_soft": {"center": (208, 208), "size": (96, 96)},
    "enclosed_pocket": {"center": (807, 694), "size": (96, 96)},
    "sand_base": {"center": (300, 1538), "size": (160, 120)},
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_hex(value: str) -> np.ndarray:
    return np.array([int(value[index:index + 2], 16) for index in (1, 3, 5)], dtype=np.float32)


def smoothstep(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def key_alpha(rgb: np.ndarray, key: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    distance = np.linalg.norm(rgb.astype(np.float32) - key[None, None, :], axis=2)
    alpha = smoothstep((distance - RADIUS_TRANSPARENT) / (RADIUS_OPAQUE - RADIUS_TRANSPARENT))
    return alpha, distance


def despill(rgb: np.ndarray, alpha: np.ndarray, key: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    out = rgb.astype(np.float32).copy()
    transition = (alpha > 0.0) & (alpha < 1.0)
    weight = (1.0 - alpha) * transition
    channel_change = np.zeros_like(out)
    dominant = np.where(key >= 250)[0].tolist()
    if dominant == [1]:
        excess = np.maximum(0.0, out[..., 1] - np.maximum(out[..., 0], out[..., 2]))
        reduction = np.minimum(excess * weight, DESPILL_CAP)
        out[..., 1] -= reduction
        channel_change[..., 1] = reduction
    elif dominant == [0, 2]:
        excess = np.maximum(0.0, np.minimum(out[..., 0], out[..., 2]) - out[..., 1])
        reduction = np.minimum(excess * weight, DESPILL_CAP)
        out[..., 0] -= reduction
        out[..., 2] -= reduction
        channel_change[..., 0] = reduction
        channel_change[..., 2] = reduction
    return np.clip(np.round(out), 0, 255).astype(np.uint8), {
        "transition_pixel_count": int(transition.sum()),
        "changed_pixel_count": int((channel_change.max(axis=2) > 0).sum()),
        "maximum_channel_change": float(channel_change.max(initial=0.0)),
        "mean_channel_change_on_changed": float(
            channel_change.max(axis=2)[channel_change.max(axis=2) > 0].mean()
        ) if (channel_change.max(axis=2) > 0).any() else 0.0,
    }


def composite(rgb: np.ndarray, alpha: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
    a = alpha[..., None]
    background = np.full_like(rgb, color, dtype=np.float32)
    return np.clip(np.round(rgb.astype(np.float32) * a + background * (1.0 - a)), 0, 255).astype(np.uint8)


def border_connected(binary: np.ndarray) -> np.ndarray:
    count, labels = cv2.connectedComponents(binary.astype(np.uint8), connectivity=8)
    if count <= 1:
        return np.zeros_like(binary, dtype=bool)
    border_labels = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    border_labels = border_labels[border_labels != 0]
    return np.isin(labels, border_labels)


def source_subject_proxy(source_rgb: np.ndarray) -> np.ndarray:
    lab = rgb2lab(source_rgb.astype(np.float32) / 255.0)
    return (np.hypot(lab[..., 1], lab[..., 2]) >= 7.0) | (lab[..., 0] <= 92.0)


def register_analysis(source_rgb: np.ndarray, candidate_white: np.ndarray, alpha: np.ndarray, rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    height, width = source_rgb.shape[:2]
    resized_white = cv2.resize(candidate_white, (width, height), interpolation=cv2.INTER_LANCZOS4)
    resized_alpha = cv2.resize(alpha.astype(np.float32), (width, height), interpolation=cv2.INTER_LINEAR)
    resized_rgb = cv2.resize(rgb, (width, height), interpolation=cv2.INTER_LANCZOS4)
    template_gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    input_gray = cv2.cvtColor(resized_white, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    warp = np.eye(2, 3, dtype=np.float32)
    try:
        correlation, warp = cv2.findTransformECC(
            template_gray,
            input_gray,
            warp,
            cv2.MOTION_AFFINE,
            (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 150, 1e-6),
            None,
            5,
        )
        registration_status = "ecc_affine"
        registration_error = None
    except cv2.error as exc:
        correlation = None
        warp = np.eye(2, 3, dtype=np.float32)
        registration_status = "resize_only_ecc_failed"
        registration_error = str(exc).split("\n")[0][:300]
    flags = cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP
    registered_rgb = cv2.warpAffine(resized_rgb, warp, (width, height), flags=flags, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    registered_alpha = cv2.warpAffine(resized_alpha, warp, (width, height), flags=flags, borderMode=cv2.BORDER_CONSTANT, borderValue=0.0)
    registered_alpha = np.clip(registered_alpha, 0.0, 1.0)
    return registered_rgb, registered_alpha, {
        "status": registration_status,
        "ecc_correlation": float(correlation) if correlation is not None else None,
        "warp_matrix": warp.tolist(),
        "error": registration_error,
    }


def tolerant_edge_metrics(source_rgb: np.ndarray, registered_white: np.ndarray) -> dict[str, float]:
    source_gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    candidate_gray = cv2.cvtColor(registered_white, cv2.COLOR_RGB2GRAY)
    source_edges = cv2.Canny(source_gray, 50, 150) > 0
    candidate_edges = cv2.Canny(candidate_gray, 50, 150) > 0
    kernel = np.ones((5, 5), dtype=np.uint8)
    source_dilated = cv2.dilate(source_edges.astype(np.uint8), kernel) > 0
    candidate_dilated = cv2.dilate(candidate_edges.astype(np.uint8), kernel) > 0
    precision = float((candidate_edges & source_dilated).sum() / max(1, candidate_edges.sum()))
    recall = float((source_edges & candidate_dilated).sum() / max(1, source_edges.sum()))
    f1 = 2.0 * precision * recall / max(1e-12, precision + recall)
    return {
        "source_edge_pixels": int(source_edges.sum()),
        "candidate_edge_pixels": int(candidate_edges.sum()),
        "tolerance_radius_px": 2,
        "precision": precision,
        "recall": recall,
        "f1": float(f1),
    }


def roi_box(center: tuple[int, int], size: tuple[int, int], bounds: tuple[int, int]) -> tuple[int, int, int, int]:
    cx, cy = center
    width, height = size
    x0 = max(0, min(bounds[0] - width, cx - width // 2))
    y0 = max(0, min(bounds[1] - height, cy - height // 2))
    return x0, y0, x0 + width, y0 + height


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "#303030")
    canvas.paste(copy.convert("RGB"), ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
    return canvas


def full_board(source: Image.Image, raw: Image.Image, reviews: dict[str, Image.Image], path: Path, title: str) -> None:
    panels = [("source", source), ("raw native", raw)] + [(name, reviews[name]) for name in ("gray", "black", "magenta", "white")]
    tile = (270, 480)
    label_h = 36
    board = Image.new("RGB", (tile[0] * len(panels), tile[1] + label_h), "#181818")
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    for column, (name, image) in enumerate(panels):
        board.paste(fit(image, tile), (column * tile[0], label_h))
        draw.text((column * tile[0] + 6, 6), name, fill="white", font=font)
    draw.text((6, 20), title, fill="#cccccc", font=font)
    board.save(path, quality=94)


def crop_boards(source_rgb: np.ndarray, registered_rgb: np.ndarray, registered_alpha: np.ndarray, directory: Path) -> dict[str, Any]:
    panels_rgb = {
        "source": source_rgb,
        "raw registered": registered_rgb,
        "gray": composite(registered_rgb, registered_alpha, (128, 128, 128)),
        "black": composite(registered_rgb, registered_alpha, (0, 0, 0)),
        "magenta": composite(registered_rgb, registered_alpha, (255, 0, 255)),
        "white": composite(registered_rgb, registered_alpha, (255, 255, 255)),
    }
    font = ImageFont.load_default()
    records = {}
    for name, spec in ROIS.items():
        box = roi_box(spec["center"], spec["size"], (source_rgb.shape[1], source_rgb.shape[0]))
        width, height = spec["size"]
        scale = 2
        label_h = 24
        board = Image.new("RGB", (width * scale * len(panels_rgb), height * scale + label_h), "#202020")
        draw = ImageDraw.Draw(board)
        for column, (panel_name, array) in enumerate(panels_rgb.items()):
            crop = Image.fromarray(array).crop(box).resize((width * scale, height * scale), Image.Resampling.NEAREST)
            board.paste(crop, (column * width * scale, label_h))
            draw.text((column * width * scale + 3, 6), panel_name, fill="white", font=font)
        board.save(directory / f"crop-{name}.png")
        records[name] = {"source_native_box": list(box), "scale_for_board": scale}
    return records


def process_candidate(record: dict[str, Any], source_rgb: np.ndarray, source_proxy: np.ndarray) -> dict[str, Any]:
    candidate_id = record["id"]
    directory = OUT / candidate_id
    raw_path = Path(record["output"]["path"])
    raw_image = Image.open(raw_path).convert("RGB")
    rgb = np.asarray(raw_image, dtype=np.uint8)
    key = parse_hex(record["target_key_hex"])
    alpha, distance = key_alpha(rgb, key)
    despilled_rgb, despill_metrics = despill(rgb, alpha, key)
    alpha_u8 = np.clip(np.round(alpha * 255.0), 0, 255).astype(np.uint8)

    no_despill_path = directory / "keyed-no-despill.png"
    keyed_path = directory / "keyed-rgba.png"
    Image.fromarray(np.dstack([rgb, alpha_u8])).save(no_despill_path)
    Image.fromarray(np.dstack([despilled_rgb, alpha_u8])).save(keyed_path)

    colors = {"gray": (128, 128, 128), "black": (0, 0, 0), "magenta": (255, 0, 255), "white": (255, 255, 255)}
    review_images = {}
    for name, color in colors.items():
        review = composite(despilled_rgb, alpha, color)
        review_images[name] = Image.fromarray(review)
        review_images[name].save(directory / f"on-{name}.png")

    white_raw = composite(despilled_rgb, alpha, (255, 255, 255))
    registered_rgb, registered_alpha, registration = register_analysis(source_rgb, white_raw, alpha, despilled_rgb)
    registered_white = composite(registered_rgb, registered_alpha, (255, 255, 255))
    Image.fromarray(registered_white).save(directory / "registered-analysis.png")

    source_gray = cv2.cvtColor(source_rgb, cv2.COLOR_RGB2GRAY)
    registered_gray = cv2.cvtColor(registered_white, cv2.COLOR_RGB2GRAY)
    ssim = float(structural_similarity(source_gray, registered_gray, data_range=255))
    edge = tolerant_edge_metrics(source_rgb, registered_white)
    registered_subject = registered_alpha >= 0.5
    union = (source_proxy | registered_subject).sum()
    silhouette_iou = float((source_proxy & registered_subject).sum() / max(1, union))
    collision_proxy = float(((registered_alpha <= 0.05) & source_proxy).sum() / max(1, source_proxy.sum()))

    keylike = distance <= RADIUS_TRANSPARENT
    connected = border_connected(keylike)
    border_size = max(1, int(round(min(rgb.shape[:2]) * 0.05)))
    border_mask = np.zeros(rgb.shape[:2], dtype=bool)
    border_mask[:border_size] = True
    border_mask[-border_size:] = True
    border_mask[:, :border_size] = True
    border_mask[:, -border_size:] = True
    border_distances = distance[border_mask]
    key_pixels = rgb[keylike]
    key_std = key_pixels.std(axis=0).tolist() if len(key_pixels) else [None, None, None]

    native_aspect = raw_image.width / raw_image.height
    source_aspect = source_rgb.shape[1] / source_rgb.shape[0]
    metrics = {
        "id": candidate_id,
        "raw": {
            "path": str(raw_path),
            "sha256": sha256(raw_path),
            "width": raw_image.width,
            "height": raw_image.height,
            "mode": raw_image.mode,
            "native_aspect": native_aspect,
            "source_aspect": source_aspect,
            "relative_aspect_error": abs(native_aspect - source_aspect) / source_aspect,
        },
        "target_key_hex": record["target_key_hex"],
        "key_method": "rgb_euclidean_to_target_only",
        "luma_used_for_keying": False,
        "transparent_radius_rgb": RADIUS_TRANSPARENT,
        "opaque_radius_rgb": RADIUS_OPAQUE,
        "alpha": {
            "fully_transparent_fraction": float((alpha <= 0.0).mean()),
            "keyable_background_fraction_alpha_le_0_05": float((alpha <= 0.05).mean()),
            "soft_fraction": float(((alpha > 0.0) & (alpha < 1.0)).mean()),
            "fully_opaque_fraction": float((alpha >= 1.0).mean()),
        },
        "chroma_plate": {
            "keylike_fraction_distance_le_30": float(keylike.mean()),
            "border_connected_keylike_fraction_of_frame": float(connected.mean()),
            "border_connected_fraction_of_keylike": float(connected.sum() / max(1, keylike.sum())),
            "enclosed_nonborder_keylike_fraction_of_frame": float((keylike & ~connected).mean()),
            "key_pixel_rgb_std": key_std,
            "border_band_px": border_size,
            "border_keylike_fraction": float((border_distances <= RADIUS_TRANSPARENT).mean()),
            "border_target_distance_mean": float(border_distances.mean()),
            "border_target_distance_p95": float(np.quantile(border_distances, 0.95)),
            "source_subject_collision_proxy_fraction": collision_proxy,
            "collision_proxy_note": "registered candidate alpha<=0.05 at source CIELAB non-paper proxy pixels; composition drift can inflate it",
        },
        "despill": {"method": "transition-only dominant-key-channel suppression", "cap_channel_levels": DESPILL_CAP, **despill_metrics},
        "registration": registration,
        "composition": {
            "registered_ssim_gray": ssim,
            "tolerant_canny_edge": edge,
            "source_proxy_vs_registered_alpha_iou": silhouette_iou,
            "metrics_are_diagnostic_not_acceptance_oracle": True,
        },
        "artifacts": {
            "keyed_no_despill": {"path": str(no_despill_path), "sha256": sha256(no_despill_path)},
            "keyed_rgba": {"path": str(keyed_path), "sha256": sha256(keyed_path)},
            "registered_analysis": str(directory / "registered-analysis.png"),
        },
    }
    metrics["roi_records"] = crop_boards(source_rgb, registered_rgb, registered_alpha, directory)
    full_board(Image.fromarray(source_rgb), raw_image, review_images, directory / "full-board.jpg", candidate_id)
    metrics_path = directory / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    return metrics


def comparison_board(source: Image.Image, metrics: list[dict[str, Any]]) -> None:
    ids = [metric["id"] for metric in metrics]
    tile = (230, 400)
    label_h = 32
    board = Image.new("RGB", (tile[0] * 3, (tile[1] + label_h) * len(ids)), "#181818")
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    for row, metric in enumerate(metrics):
        directory = OUT / metric["id"]
        raw = Image.open(metric["raw"]["path"]).convert("RGB")
        keyed = Image.open(directory / "on-magenta.png").convert("RGB")
        panels = (("source", source), ("raw", raw), ("keyed on magenta", keyed))
        for column, (name, image) in enumerate(panels):
            y = row * (tile[1] + label_h)
            board.paste(fit(image, tile), (column * tile[0], y + label_h))
            draw.text((column * tile[0] + 5, y + 5), f"{metric['id']} | {name}", fill="white", font=font)
    board.save(OUT / "comparison-board.png")


def main() -> None:
    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    source_image = Image.open(SOURCE).convert("RGB")
    source_rgb = np.asarray(source_image, dtype=np.uint8)
    proxy = source_subject_proxy(source_rgb)
    records = [record for record in manifest["new_candidates"] if record.get("status") == "valid_output"] + [manifest["baseline"]]
    metrics = [process_candidate(record, source_rgb, proxy) for record in records]
    comparison_board(source_image, metrics)
    manifest["processed_candidate_ids"] = [metric["id"] for metric in metrics]
    manifest["processing"] = {
        "key_method": "rgb_euclidean_to_target_only",
        "luma_used_for_keying": False,
        "transparent_radius_rgb": RADIUS_TRANSPARENT,
        "opaque_radius_rgb": RADIUS_OPAQUE,
        "despill_cap_channel_levels": DESPILL_CAP,
        "comparison_board": str(OUT / "comparison-board.png"),
        "comparison_board_sha256": sha256(OUT / "comparison-board.png"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"PROCESS_OK candidates={len(metrics)} ids={manifest['processed_candidate_ids']}")


if __name__ == "__main__":
    main()
