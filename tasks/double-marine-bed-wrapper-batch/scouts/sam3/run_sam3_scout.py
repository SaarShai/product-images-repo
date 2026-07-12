#!/usr/bin/env python3
"""One-request SAM 3 semantic-mask scout for native image 14.

`request` performs one guarded fal segmentation call and downloads every mask.
`build` is offline-only and unions explicitly selected returned masks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "scripts"))
from _falcommon import load_fal_key  # noqa: E402

ENDPOINT = "fal-ai/sam-3/image"
PROMPT = (
    "the complete watercolor marine illustration, including every coral, "
    "seaweed, fish, shell, bubble, rock, sandy seabed, and pale painted "
    "watercolor wash; exclude only blank white paper"
)
MAX_MASKS = 32
ESTIMATED_COST_USD = 0.005
SOURCE_SHA256 = "925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d"
DEFAULT_SOURCE = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
)
DEFAULT_OUT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/candidates/image14-research/sam3-scout"
)

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


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_error(exc: BaseException) -> str:
    message = str(exc)
    message = re.sub(r"https?://\S+", "[redacted-url]", message)
    message = re.sub(r"(?i)(key|token|authorization)[=: ]+\S+", r"\1=[redacted]", message)
    return message[:500]


def mask_channel(image: Image.Image) -> tuple[Image.Image, str]:
    if "A" in image.getbands():
        alpha = image.getchannel("A")
        if alpha.getextrema()[0] != alpha.getextrema()[1]:
            return alpha, "alpha"
    return image.convert("L"), "luminance"


def map_mask(mask: Image.Image, source_size: tuple[int, int]) -> tuple[Image.Image, dict[str, Any]]:
    sw, sh = source_size
    mw, mh = mask.size
    source_ratio = sw / sh
    mask_ratio = mw / mh
    if abs(source_ratio - mask_ratio) / source_ratio <= 0.025:
        mapped = mask.resize(source_size, Image.Resampling.BILINEAR)
        return mapped, {
            "method": "direct_aspect_preserving_resize",
            "raw_size": [mw, mh],
            "crop_box": [0, 0, mw, mh],
        }

    scale = min(mw / sw, mh / sh)
    content_w = max(1, int(round(sw * scale)))
    content_h = max(1, int(round(sh * scale)))
    left = (mw - content_w) // 2
    top = (mh - content_h) // 2
    crop_box = (left, top, left + content_w, top + content_h)
    mapped = mask.crop(crop_box).resize(source_size, Image.Resampling.BILINEAR)
    return mapped, {
        "method": "centered_letterbox_crop_then_resize",
        "raw_size": [mw, mh],
        "crop_box": list(crop_box),
    }


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.copy()
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "#252525")
    canvas.paste(copy.convert("RGB"), ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
    return canvas


def make_contact_sheet(source: Image.Image, masks: list[Path], out: Path) -> list[dict[str, Any]]:
    font = ImageFont.load_default()
    card_w, card_h = 420, 440
    cols = 4
    rows = (len(masks) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * card_w, rows * card_h), "#151515")
    records: list[dict[str, Any]] = []
    src_arr = np.asarray(source.convert("RGB"), dtype=np.float32)
    for index, path in enumerate(masks):
        with Image.open(path) as raw:
            channel, channel_name = mask_channel(raw)
            mapped, mapping = map_mask(channel, source.size)
        mask_arr = np.asarray(mapped, dtype=np.uint8)
        keep = mask_arr >= 128
        overlay = src_arr.copy()
        overlay[keep] = overlay[keep] * 0.55 + np.array([30, 255, 80], dtype=np.float32) * 0.45
        overlay[~keep] = overlay[~keep] * 0.65 + np.array([255, 30, 120], dtype=np.float32) * 0.35
        overlay_im = Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8))
        card = Image.new("RGB", (card_w, card_h), "#303030")
        card.paste(fit(mapped.convert("RGB"), (200, 390)), (5, 40))
        card.paste(fit(overlay_im, (200, 390)), (215, 40))
        draw = ImageDraw.Draw(card)
        draw.text((8, 8), f"mask {index:02d} | white=selected | {channel_name}", fill="white", font=font)
        draw.text((8, 24), f"coverage={keep.mean():.4f} | {mapping['method']}", fill="#d0d0d0", font=font)
        x = (index % cols) * card_w
        y = (index // cols) * card_h
        sheet.paste(card, (x, y))
        records.append({
            "index": index,
            "channel": channel_name,
            "coverage_fraction_at_native": float(keep.mean()),
            "mapping": mapping,
        })
    sheet.save(out / "per-mask-contact-sheet.png")
    return records


def request_once(source_path: Path, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    attempt_path = out / "request-attempt.json"
    if attempt_path.exists():
        raise SystemExit(f"refusing second request: attempt record already exists at {attempt_path}")

    source_hash = sha256(source_path)
    with Image.open(source_path) as image:
        source = image.convert("RGB")
        source_size = source.size
    if source_hash != SOURCE_SHA256 or source_size != (941, 1672):
        raise SystemExit(f"source identity mismatch: sha256={source_hash} size={source_size}")

    arguments = {
        "prompt": PROMPT,
        "return_multiple_masks": True,
        "max_masks": MAX_MASKS,
        "include_scores": True,
        "include_boxes": True,
        "apply_mask": False,
        "output_format": "png",
    }
    attempt = {
        "endpoint": ENDPOINT,
        "request_count": 1,
        "status": "started",
        "started_at_utc": utc_now(),
        "source_path": str(source_path),
        "source_sha256": source_hash,
        "source_size": list(source_size),
        "prompt": PROMPT,
        "arguments_without_image_url": arguments,
        "upload_method": "fal_client.upload_file",
        "estimated_cost_usd": ESTIMATED_COST_USD,
    }
    write_json(attempt_path, attempt)

    upload_started = time.perf_counter()
    try:
        import fal_client

        os.environ["FAL_KEY"] = load_fal_key()
        uploaded_url = fal_client.upload_file(source_path)
        upload_seconds = time.perf_counter() - upload_started
        request_ids: list[str] = []
        request_started = time.perf_counter()
        response = fal_client.subscribe(
            ENDPOINT,
            arguments={"image_url": uploaded_url, **arguments},
            with_logs=False,
            on_enqueue=lambda request_id: request_ids.append(str(request_id)),
            client_timeout=300,
        )
        request_seconds = time.perf_counter() - request_started
    except BaseException as exc:
        attempt.update({
            "status": "failed",
            "finished_at_utc": utc_now(),
            "error_type": type(exc).__name__,
            "error": safe_error(exc),
            "duration_seconds_before_failure": round(time.perf_counter() - upload_started, 6),
        })
        write_json(attempt_path, attempt)
        raise

    masks_value = response.get("masks") if isinstance(response, dict) else None
    masks = masks_value if isinstance(masks_value, list) else []
    raw_dir = out / "raw-masks"
    raw_dir.mkdir(exist_ok=True)
    mask_records = []
    for index, item in enumerate(masks):
        if not isinstance(item, dict) or not item.get("url"):
            raise RuntimeError(f"response mask {index} has no downloadable URL")
        download_started = time.perf_counter()
        download = requests.get(item["url"], timeout=120)
        download.raise_for_status()
        content = download.content
        raw_path = raw_dir / f"mask-{index:02d}.png"
        raw_path.write_bytes(content)
        with Image.open(BytesIO(content)) as mask_image:
            raw_size = list(mask_image.size)
            raw_mode = mask_image.mode
            mask_image.verify()
        mask_records.append({
            "index": index,
            "local_path": str(raw_path.relative_to(out)),
            "sha256": hashlib.sha256(content).hexdigest(),
            "downloaded_bytes": len(content),
            "raw_size": raw_size,
            "raw_mode": raw_mode,
            "response_content_type": item.get("content_type"),
            "response_file_name": item.get("file_name"),
            "response_file_size": item.get("file_size"),
            "response_width": item.get("width"),
            "response_height": item.get("height"),
            "download_seconds": round(time.perf_counter() - download_started, 6),
        })

    response_keys = sorted(response.keys()) if isinstance(response, dict) else []
    metadata = response.get("metadata", []) if isinstance(response, dict) else []
    scores = response.get("scores", []) if isinstance(response, dict) else []
    boxes = response.get("boxes", []) if isinstance(response, dict) else []
    summary = {
        "endpoint": ENDPOINT,
        "request_id": request_ids[-1] if request_ids else None,
        "response_top_level_keys": response_keys,
        "response_shape": {key: type(response[key]).__name__ for key in response_keys},
        "mask_count": len(masks),
        "masks": mask_records,
        "scores": scores,
        "boxes": boxes,
        "metadata": metadata,
        "upload_seconds": round(upload_seconds, 6),
        "segmentation_request_seconds": round(request_seconds, 6),
        "total_seconds_before_artifacts": round(time.perf_counter() - upload_started, 6),
        "estimated_cost_usd": ESTIMATED_COST_USD,
    }
    write_json(out / "response-summary.json", summary)
    contact_records = make_contact_sheet(source, sorted(raw_dir.glob("mask-*.png")), out)
    write_json(out / "mask-inspection-metadata.json", contact_records)
    attempt.update({
        "status": "succeeded",
        "finished_at_utc": utc_now(),
        "request_id": summary["request_id"],
        "response_mask_count": len(masks),
        "upload_seconds": summary["upload_seconds"],
        "segmentation_request_seconds": summary["segmentation_request_seconds"],
        "total_seconds_before_artifacts": summary["total_seconds_before_artifacts"],
    })
    write_json(attempt_path, attempt)
    print(
        f"SAM3_REQUEST_OK request_count=1 masks={len(masks)} "
        f"request_seconds={request_seconds:.3f} cost_estimate_usd={ESTIMATED_COST_USD:.3f}"
    )


def parse_selection(value: str, count: int) -> list[int]:
    if value.strip().lower() == "all":
        return list(range(count))
    selected = sorted({int(part.strip()) for part in value.split(",") if part.strip()})
    if not selected or selected[0] < 0 or selected[-1] >= count:
        raise SystemExit(f"invalid selected indices for mask count {count}: {selected}")
    return selected


def composite(rgb: np.ndarray, alpha: np.ndarray, color: tuple[int, int, int]) -> Image.Image:
    a = alpha.astype(np.float32)[..., None] / 255.0
    bg = np.full_like(rgb, color, dtype=np.float32)
    out = rgb.astype(np.float32) * a + bg * (1.0 - a)
    return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8))


def roi_box(center: tuple[int, int], size: tuple[int, int], bounds: tuple[int, int]) -> tuple[int, int, int, int]:
    cx, cy = center
    w, h = size
    x0 = max(0, min(bounds[0] - w, cx - w // 2))
    y0 = max(0, min(bounds[1] - h, cy - h // 2))
    return x0, y0, x0 + w, y0 + h


def build_union(source_path: Path, out: Path, selected_value: str, reason: str) -> None:
    attempt = json.loads((out / "request-attempt.json").read_text())
    summary = json.loads((out / "response-summary.json").read_text())
    if attempt.get("status") != "succeeded" or attempt.get("request_count") != 1:
        raise SystemExit("request did not succeed exactly once")
    selected = parse_selection(selected_value, int(summary["mask_count"]))
    with Image.open(source_path) as image:
        source = image.convert("RGB")
    native_masks = []
    mapping_records = []
    native_dir = out / "native-masks"
    native_dir.mkdir(exist_ok=True)
    for record in summary["masks"]:
        index = int(record["index"])
        with Image.open(out / record["local_path"]) as raw:
            channel, channel_name = mask_channel(raw)
            mapped, mapping = map_mask(channel, source.size)
        native_path = native_dir / f"mask-{index:02d}.png"
        mapped.save(native_path)
        native_masks.append(np.asarray(mapped, dtype=np.uint8))
        mapping_records.append({"index": index, "channel": channel_name, **mapping})
    union = np.maximum.reduce([native_masks[index] for index in selected])
    union_path = out / "union-mask.png"
    Image.fromarray(union).save(union_path)

    rgb = np.asarray(source, dtype=np.uint8)
    rgba = np.dstack([rgb, union])
    alpha_path = out / "alpha-cutout.png"
    Image.fromarray(rgba).save(alpha_path)

    backgrounds = {
        "gray": (128, 128, 128),
        "black": (0, 0, 0),
        "magenta": (255, 0, 255),
        "white": (255, 255, 255),
    }
    reviews: dict[str, Image.Image] = {}
    for name, color in backgrounds.items():
        reviews[name] = composite(rgb, union, color)
        reviews[name].save(out / f"review-{name}.png")

    keep = union >= 128
    overlay = rgb.astype(np.float32)
    overlay[keep] = overlay[keep] * 0.55 + np.array([30, 255, 80], dtype=np.float32) * 0.45
    overlay[~keep] = overlay[~keep] * 0.65 + np.array([255, 30, 120], dtype=np.float32) * 0.35
    Image.fromarray(np.clip(overlay, 0, 255).astype(np.uint8)).save(out / "union-overlay.png")

    font = ImageFont.load_default()
    roi_records = {}
    panels = [("source", source)] + [(name, reviews[name]) for name in ("gray", "black", "magenta", "white")]
    for name, spec in ROIS.items():
        box = roi_box(spec["center"], spec["size"], source.size)
        tile_w, tile_h = spec["size"]
        label_h = 22
        board = Image.new("RGB", (tile_w * len(panels), tile_h + label_h), "#202020")
        draw = ImageDraw.Draw(board)
        for col, (panel_name, panel) in enumerate(panels):
            crop = panel.crop(box)
            board.paste(crop, (col * tile_w, label_h))
            draw.text((col * tile_w + 3, 5), panel_name, fill="white", font=font)
        board.save(out / f"roi-{name}.png")
        roi_records[name] = {"box_native": list(box), "board_panels": [p[0] for p in panels]}

    build_summary = {
        "source_path": str(source_path),
        "source_sha256": sha256(source_path),
        "source_size": list(source.size),
        "selected_mask_indices": selected,
        "selection_reason": reason,
        "selection_inputs": ["per-mask-contact-sheet.png", "raw-masks", "provider prompt and metadata"],
        "held_out_benchmark_used_for_selection": False,
        "mask_mappings": mapping_records,
        "union_coverage_fraction_alpha_gt_127": float(keep.mean()),
        "union_soft_fraction_alpha_between_0_and_255": float(((union > 0) & (union < 255)).mean()),
        "artifacts_are_semantic_proposal_only": True,
        "matting_performed": False,
        "color_decontamination_performed": False,
        "roi_records": roi_records,
    }
    write_json(out / "build-summary.json", build_summary)
    print(
        f"SAM3_BUILD_OK selected={selected} union_coverage={keep.mean():.6f} "
        f"native_size={source.size[0]}x{source.size[1]}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    request_parser = sub.add_parser("request")
    request_parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    request_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    build_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    build_parser.add_argument("--selected", required=True, help="comma-separated returned-mask indices, or 'all'")
    build_parser.add_argument("--reason", required=True, help="selection rationale based only on returned masks/prompt")
    args = parser.parse_args()
    if args.command == "request":
        request_once(args.source, args.out)
    else:
        build_union(args.source, args.out, args.selected, args.reason)


if __name__ == "__main__":
    main()
