#!/usr/bin/env python3
"""Object-aware recovery prototype for image14 (prototype).

Starts from the BRIA hard180 candidate and generates bounded recovery candidates.
SAM is attempted first when available. When unavailable, deterministic local
proxy candidates are still produced. Output is always restricted to
`Images/candidates/image14-object-aware/`.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None


PRODUCT_DIR = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)

BASELINE_CANDIDATE = PRODUCT_DIR / (
    "Images/candidates/image14-research/candidates/"
    "14-01-bria-rmbg-alpha-matting-hard180.png"
)
X4_RGB = PRODUCT_DIR / (
    "Images/candidates/batch-x8-hard180/x4-rgb/"
    "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
)
OUT_ROOT = PRODUCT_DIR / "Images/candidates/image14-object-aware"


@dataclass(frozen=True)
class CandidateSpec:
    slug: str
    label: str
    method: str
    build: Callable[[np.ndarray, np.ndarray], tuple[np.ndarray, dict[str, Any]]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate object-aware recovery candidates for image14."
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=BASELINE_CANDIDATE,
        help="Input BRIA hard180 RGBA candidate.",
    )
    parser.add_argument(
        "--x4-rgb",
        type=Path,
        default=X4_RGB,
        help="x4 RGB reference used for object recovery heuristics.",
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=OUT_ROOT,
        help="Output directory root under Images/candidates/image14-object-aware.",
    )
    parser.add_argument("--no-sam", action="store_true", help="Skip SAM and run proxies only.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing candidate files.")
    return parser.parse_args()


def ensure_paths(out_root: Path) -> dict[str, Path]:
    root = out_root.expanduser().resolve()
    paths = {
        "root": root,
        "candidates": root / "candidates",
        "review": root / "review",
        "diagnostics": root / "diagnostics",
        "manifest": root / "manifest.json",
        "failure": root / "diagnostics" / "failure.json",
    }
    for key in ("candidates", "review", "diagnostics"):
        paths[key].mkdir(parents=True, exist_ok=True)
    return paths


def get_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def load_inputs(
    baseline_path: Path, x4_rgb_path: Path
) -> tuple[tuple[np.ndarray, np.ndarray], np.ndarray]:
    baseline_img = Image.open(baseline_path).convert("RGBA")
    baseline_rgb = np.asarray(baseline_img.convert("RGB"))
    baseline_alpha = np.asarray(baseline_img.getchannel("A")) >= 128
    x4_rgb = np.asarray(Image.open(x4_rgb_path).convert("RGB"))
    return (baseline_rgb, baseline_alpha), x4_rgb


def hsv_proxy(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    arr = rgb.astype(np.float32) / 255.0
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    sat = np.zeros_like(mx)
    nz = mx > 0
    sat[nz] = (mx[nz] - mn[nz]) / mx[nz]
    return sat, mx


def resize_bool(mask_bool: np.ndarray, size_xy: tuple[int, int], down: bool = False) -> np.ndarray:
    img = Image.fromarray(mask_bool.astype(np.uint8) * 255, "L")
    mode = Image.Resampling.NEAREST
    out = img.resize(size_xy, mode) if down else img.resize(size_xy, mode)
    return np.asarray(out) >= 128


def remove_tiny(mask: np.ndarray, min_area: int) -> tuple[np.ndarray, int]:
    if min_area <= 1:
        return mask, 0
    labels, count = ndi.label(mask)
    if count == 0:
        return mask, 0
    areas = np.bincount(labels.ravel())
    remove = np.where((areas > 0) & (areas < min_area))[0]
    remove = remove[remove != 0]
    if remove.size == 0:
        return mask, 0
    out = mask.copy()
    removed_mask = np.isin(labels, remove)
    out[removed_mask] = False
    return out, int(removed_mask.sum())


def find_true_holes(mask: np.ndarray) -> np.ndarray:
    bg = ~mask
    labels, count = ndi.label(bg)
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    border = np.zeros_like(bg, dtype=bool)
    border[0, :] = True
    border[-1, :] = True
    border[:, 0] = True
    border[:, -1] = True
    touch_border = np.zeros(count + 1, dtype=bool)
    touch_border[np.unique(labels[border])] = True
    holes = np.zeros_like(mask, dtype=bool)
    for label_id in range(1, count + 1):
        if not touch_border[label_id]:
            holes |= labels == label_id
    return holes


def background_mask(rgb: np.ndarray) -> np.ndarray:
    sat, val = hsv_proxy(rgb)
    spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    return (val >= 0.94) & (sat <= 0.16) & (spread <= 42)


def color_consensus_restore(mask: np.ndarray, rgb: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    sat, val = hsv_proxy(rgb)
    holes = find_true_holes(mask)
    band = ndi.binary_dilation(mask, iterations=8) & ~mask
    band &= ~holes

    dist_fg, (gy, gx) = ndi.distance_transform_edt(~mask, return_indices=True)
    nearest_color = rgb[gy, gx].astype(np.float32)
    color_delta = np.linalg.norm(rgb.astype(np.float32) - nearest_color, axis=2)

    restore = band & (dist_fg <= 11) & (color_delta <= 70.0) & (sat >= 0.055) & (val <= 0.985)
    restore &= ndi.binary_dilation(mask, iterations=1)
    restore &= ~holes
    restore = ndi.binary_opening(restore, iterations=1)
    restore, removed = remove_tiny(restore, min_area=72)

    return restore, {
        "method": "color_consensus",
        "band_px": int(band.sum()),
        "restore_px": int(restore.sum()),
        "tiny_removed_px": removed,
        "max_color_delta": float(color_delta[restore].max()) if restore.any() else 0.0,
    }


def edge_structure_restore(mask: np.ndarray, rgb: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    sat, val = hsv_proxy(rgb)
    bg = background_mask(rgb)
    holes = find_true_holes(mask)

    gray = rgb.astype(np.float32).mean(axis=2)
    edge = np.hypot(ndi.sobel(gray, axis=0), ndi.sobel(gray, axis=1))
    if edge.max() > 0:
        edge /= edge.max()

    band = ndi.binary_dilation(mask, iterations=7) & ~mask
    band &= ~bg
    band &= ~holes

    restore = band & (((edge >= 0.16) | (sat >= 0.19)) & (val <= 0.985))
    restore &= ndi.binary_dilation(mask, iterations=1)
    restore = ndi.binary_opening(restore, iterations=1)
    restore &= ~holes
    restore, removed = remove_tiny(restore, min_area=64)

    return restore, {
        "method": "edge_structure",
        "band_px": int(band.sum()),
        "restore_px": int(restore.sum()),
        "tiny_removed_px": removed,
        "edge_max": float(edge[restore].max()) if restore.any() else 0.0,
    }


def consensus_restore(mask: np.ndarray, rgb: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    sat, val = hsv_proxy(rgb)
    gray = rgb.astype(np.float32).mean(axis=2)
    edge = np.hypot(ndi.sobel(gray, axis=0), ndi.sobel(gray, axis=1))
    if edge.max() > 0:
        edge /= edge.max()

    dist_fg, (gy, gx) = ndi.distance_transform_edt(~mask, return_indices=True)
    nearest_color = rgb[gy, gx].astype(np.float32)
    color_delta = np.linalg.norm(rgb.astype(np.float32) - nearest_color, axis=2)

    holes = find_true_holes(mask)
    band = ndi.binary_dilation(mask, iterations=10) & ~mask
    band &= ~holes

    votes = (
        (color_delta <= 85.0).astype(np.uint8)
        + (edge >= 0.11).astype(np.uint8)
        + (sat >= 0.08).astype(np.uint8)
        + (val <= 0.985).astype(np.uint8)
    )
    restore = band & (votes >= 3) & (dist_fg <= 14)
    restore &= ndi.binary_dilation(mask, iterations=1)
    restore = ndi.binary_opening(restore, iterations=1)
    restore &= ~holes
    restore, removed = remove_tiny(restore, min_area=96)

    return restore, {
        "method": "consensus",
        "band_px": int(band.sum()),
        "restore_px": int(restore.sum()),
        "tiny_removed_px": removed,
        "vote_max": int(votes[restore].max()) if restore.any() else 0,
    }


def loose_adjacency_restore(mask: np.ndarray, rgb: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    sat, val = hsv_proxy(rgb)
    holes = find_true_holes(mask)
    bg = background_mask(rgb)
    band = ndi.binary_dilation(mask, iterations=5) & ~mask
    band = band & ~holes
    band &= ~bg
    adj = ndi.binary_dilation(mask, iterations=1)
    candidates = band & adj
    candidates &= (val >= 0.05) & (sat >= 0.01)
    candidates, removed = remove_tiny(candidates, min_area=4)

    return candidates, {
        "method": "loose_adjacency",
        "band_px": int(band.sum()),
        "restore_px": int(candidates.sum()),
        "tiny_removed_px": removed,
        "sat_px": int((sat >= 0.01).sum()),
    }


def run_sam(mask: np.ndarray, rgb: np.ndarray) -> tuple[bool, np.ndarray, dict[str, Any]]:
    try:
        import torch
        from segment_anything import SamPredictor, sam_model_registry
    except Exception as exc:  # noqa: BLE001
        return False, np.zeros_like(mask, dtype=bool), {
            "method": "sam",
            "status": "unavailable",
            "reason": f"missing_dependency:{type(exc).__name__}",
        }

    candidate_ckpts = [
        Path.home() / ".cache/segment_anything/sam_vit_h_4b8939.pth",
        Path.home() / ".cache/segment_anything/sam_vit_b_01ec64.pth",
        Path.home() / ".cache/segment_anything/sam_vit_l_0b3195.pth",
        Path("/tmp/sam_vit_h_4b8939.pth"),
        Path("/tmp/sam_vit_b_01ec64.pth"),
        Path("/tmp/sam_vit_l_0b3195.pth"),
    ]
    checkpoint = next((p for p in candidate_ckpts if p.exists()), None)
    if checkpoint is None:
        return False, np.zeros_like(mask, dtype=bool), {
            "method": "sam",
            "status": "unavailable",
            "reason": "no_checkpoint_found",
        }

    ys, xs = np.where(mask)
    if xs.size == 0 or ys.size == 0:
        return False, np.zeros_like(mask, dtype=bool), {
            "method": "sam",
            "status": "blocked",
            "reason": "empty_input_mask",
        }

    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    if x1 <= x0 or y1 <= y0:
        return False, np.zeros_like(mask, dtype=bool), {
            "method": "sam",
            "status": "blocked",
            "reason": "invalid_bbox",
        }

    model_key = "vit_h"
    if "sam_vit_b" in checkpoint.name:
        model_key = "vit_b"
    elif "sam_vit_l" in checkpoint.name:
        model_key = "vit_l"

    try:
        model = sam_model_registry[model_key](checkpoint=str(checkpoint))
        if torch.cuda.is_available():
            model = model.to("cuda")
        predictor = SamPredictor(model)
        predictor.set_image(rgb)

        point = np.array([[(x0 + x1) / 2.0, (y0 + y1) / 2.0]], dtype=np.float32)
        labels = np.array([1], dtype=np.int64)
        masks, _, _ = predictor.predict(
            point_coords=point,
            point_labels=labels,
            multimask_output=True,
            return_logits=False,
        )
        if masks is None or len(masks) == 0:
            return False, np.zeros_like(mask, dtype=bool), {
                "method": "sam",
                "status": "no_masks",
                "reason": "predict_empty",
                "checkpoint": str(checkpoint),
            }

        base_bool = mask
        best_overlap = 0
        best_i = 0
        for idx, candidate in enumerate(masks.astype(bool)):
            overlap = int(np.logical_and(candidate, base_bool).sum())
            if overlap > best_overlap:
                best_overlap = overlap
                best_i = idx

        sam_mask = masks[best_i].astype(bool)
        sam_mask = ndi.binary_dilation(sam_mask, iterations=1)
        return True, sam_mask, {
            "method": "sam",
            "status": "ok",
            "checkpoint": str(checkpoint),
            "overlap_px": int(best_overlap),
            "restore_px": int((sam_mask & ~base_bool).sum()),
            "total_px": int(sam_mask.sum()),
        }
    except Exception as exc:  # noqa: BLE001
        return False, np.zeros_like(mask, dtype=bool), {
            "method": "sam",
            "status": "error",
            "reason": f"sam_invoke_{type(exc).__name__}",
        }


def write_x8_candidate(base_rgb: np.ndarray, alpha_bool: np.ndarray, out_path: Path) -> None:
    base = Image.fromarray(base_rgb, "RGB").convert("RGBA")
    base.putalpha(Image.fromarray(alpha_bool.astype(np.uint8) * 255, "L"))
    base.save(out_path)


def alpha_stats(alpha_bool: np.ndarray) -> dict[str, int | bool]:
    alpha_u8 = alpha_bool.astype(np.uint8) * 255
    hist = np.bincount(alpha_u8.ravel(), minlength=256)
    return {
        "is_binary_alpha": bool(hist[1:255].sum() == 0),
        "semi_alpha_px": int(hist[1:255].sum()),
        "opaque_px": int(hist[255]),
        "transparent_px": int(hist[0]),
        "nonempty_px": int(alpha_bool.sum()),
    }


def composite_thumb(path: Path, max_side: int = 500) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    bg = Image.new("RGB", im.size, (96, 96, 96))
    bg.paste(im, (0, 0), im)
    scale = min(1.0, max_side / max(im.size))
    if scale < 1.0:
        bg = bg.resize((max(1, int(bg.width * scale)), max(1, int(bg.height * scale))), Image.Resampling.LANCZOS)
    tile = Image.new("RGB", (520, 760), (220, 220, 220))
    tile.paste(bg, ((520 - bg.width) // 2, (760 - bg.height) // 2))
    return tile


def build_review_sheet(items: list[dict[str, Any]], out_path: Path) -> None:
    if not items:
        return
    cols = len(items)
    sheet = Image.new("RGB", (520 * cols, 840), (240, 240, 240))
    draw = ImageDraw.Draw(sheet)
    font = get_font(15)
    for idx, item in enumerate(items):
        x = idx * 520
        draw.rectangle((x, 0, x + 520, 42), fill=(255, 255, 255))
        label = item.get("label", item.get("slug", "candidate"))[:50]
        draw.text((x + 8, 12), label, fill=(0, 0, 0), font=font)
        thumb = composite_thumb(Path(item["candidate_rgba"]))
        sheet.paste(thumb, (x, 52))

        method = item.get("metrics", {}).get("method", item.get("method", ""))
        restore = int(item.get("restore_px", 0))
        draw.text((x + 8, 812), f"method={method}", fill=(0, 0, 0), font=font)
        draw.text((x + 8, 832), f"restore={restore}", fill=(0, 0, 0), font=font)

    sheet.save(out_path, quality=95)


def main() -> int:
    args = parse_args()
    paths = ensure_paths(args.out_root)

    baseline_path = args.baseline.expanduser().resolve()
    x4_rgb_path = args.x4_rgb.expanduser().resolve()
    missing = [p for p in (baseline_path, x4_rgb_path) if not p.exists()]
    if missing:
        print("FAIL: missing input(s):")
        for p in missing:
            print(f"  - {p}")
        return 1

    (baseline_rgb, base_alpha), x4_rgb = load_inputs(baseline_path, x4_rgb_path)
    x8_size = (base_alpha.shape[1], base_alpha.shape[0])
    x4_mask = resize_bool(base_alpha, x4_rgb.shape[1::-1])
    x4_mask, removed = remove_tiny(x4_mask, min_area=256)

    specs: list[CandidateSpec] = [
        CandidateSpec("01-loose-adjacency", "loose-adjacency proxy", "proxy", loose_adjacency_restore),
        CandidateSpec("02-color-consensus", "color-consensus proxy", "proxy", color_consensus_restore),
        CandidateSpec("03-edge-structure", "edge-structure proxy", "proxy", edge_structure_restore),
        CandidateSpec("04-consensus", "consensus proxy", "proxy", consensus_restore),
    ]

    report: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    if not args.no_sam:
        ok, sam_mask, sam_meta = run_sam(x4_mask, x4_rgb)
        diagnostics.append(
            {
                "method": "sam",
                "attempted": True,
                "status": "ok" if ok else sam_meta.get("status", "unavailable"),
                "meta": sam_meta,
            }
        )
        if ok:
            add = (sam_mask & ~x4_mask)
            add_x8 = resize_bool(add, x8_size)
            out_alpha = base_alpha | add_x8
            if out_alpha.any():
                out_path = paths["candidates"] / "14-image14-object-aware-00-sam-proxy.png"
                if (not out_path.exists()) or args.force:
                    write_x8_candidate(baseline_rgb, out_alpha, out_path)
                bbox = Image.fromarray((out_alpha.astype(np.uint8) * 255)).getbbox() or (0, 0, 0, 0)
                stats = alpha_stats(out_alpha)
                report.append(
                    {
                        "slug": "00-sam-proxy",
                        "label": "sam recover proxy",
                        "method": "sam",
                        "baseline": str(baseline_path),
                        "candidate_rgba": str(out_path),
                        "restore_px": int(add_x8.sum()),
                        "added_px": int(add_x8.sum()),
                        "alpha_nonempty": int(out_alpha.sum()),
                        "bbox_nonzero": list(map(int, bbox)),
                        "metrics": {"method": "sam", "details": sam_meta},
                        "is_binary_alpha": stats["is_binary_alpha"],
                        "semi_alpha_px": stats["semi_alpha_px"],
                        "opaque_px": stats["opaque_px"],
                        "transparent_px": stats["transparent_px"],
                    }
                )
            else:
                diagnostics.append({"method": "sam", "status": "no-op", "reason": "no new pixels"})

    consecutive_failures = 0
    for spec in specs:
        try:
            add_x4, meta = spec.build(x4_mask, x4_rgb)
            add_x8 = resize_bool(add_x4, x8_size)
            add_x8 &= ~base_alpha
            out_alpha = base_alpha | add_x8
            if not add_x8.any():
                consecutive_failures += 1
                diagnostics.append({"method": spec.method, "slug": spec.slug, "status": "no-op", "meta": meta})
                if consecutive_failures >= 2:
                    break
                continue

            consecutive_failures = 0
            out_path = paths["candidates"] / f"14-image14-object-aware-{spec.slug}.png"
            if out_path.exists() and not args.force:
                diagnostics.append({"method": spec.method, "slug": spec.slug, "status": "skipped", "reason": "exists"})
                continue

            write_x8_candidate(baseline_rgb, out_alpha, out_path)
            diag_mask = paths["diagnostics"] / f"{spec.slug}-add-mask.png"
            Image.fromarray((add_x4.astype(np.uint8) * 255), "L").save(diag_mask)

            bbox = Image.fromarray((out_alpha.astype(np.uint8) * 255)).getbbox() or (0, 0, 0, 0)
            stats = alpha_stats(out_alpha)
            report.append(
                {
                    "slug": spec.slug,
                    "label": spec.label,
                    "method": spec.method,
                    "baseline": str(baseline_path),
                    "candidate_rgba": str(out_path),
                    "restore_px": int(add_x8.sum()),
                    "added_px": int(add_x8.sum()),
                    "alpha_nonempty": int(out_alpha.sum()),
                    "bbox_nonzero": list(map(int, bbox)),
                    "diagnostics_mask": str(diag_mask),
                    "is_binary_alpha": stats["is_binary_alpha"],
                    "semi_alpha_px": stats["semi_alpha_px"],
                    "opaque_px": stats["opaque_px"],
                    "transparent_px": stats["transparent_px"],
                    "metrics": meta,
                }
            )
            diagnostics.append({"method": spec.method, "slug": spec.slug, "status": "ok", "meta": meta})
        except Exception as exc:  # noqa: BLE001
            consecutive_failures += 1
            diagnostics.append({"method": spec.method, "slug": spec.slug, "status": "error", "reason": f"{type(exc).__name__}: {exc}"})
            if consecutive_failures >= 2:
                break

    review_items = [
        {
            "slug": "00-baseline",
            "label": "baseline-hard180",
            "candidate_rgba": str(baseline_path),
            "restore_px": 0,
            "metrics": {"method": "baseline"},
        }
    ]
    for item in report:
        review_items.append(
            {
                "slug": item["slug"],
                "label": item["label"],
                "candidate_rgba": item["candidate_rgba"],
                "restore_px": item["restore_px"],
                "metrics": item.get("metrics", {}),
            }
        )

    board_path = paths["review"] / "14-image14-object-aware-contact-sheet.jpg"
    build_review_sheet(review_items, board_path)

    manifest = {
        "goal": "image14 object-aware recovery prototype",
        "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "baseline": str(baseline_path),
        "x4_rgb": str(x4_rgb_path),
        "out_root": str(paths["root"]),
        "baseline_tiny_removed_px": removed,
        "sam_attempted": bool(not args.no_sam),
        "candidates": report,
        "diagnostics": diagnostics,
        "review": {
            "contact_sheet": str(board_path),
            "count": len(review_items),
        },
        "candidate_count": len(report),
        "baseline_alpha": {
            "size": [int(base_alpha.shape[1]), int(base_alpha.shape[0])],
            **alpha_stats(base_alpha),
        },
        "status": "ok" if report else "blocked",
    }

    paths["manifest"].write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if not report:
        paths["failure"].write_text(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "reason": "no_object_aware_restores",
                    "diagnostics": diagnostics,
                    "out_root": str(paths["root"]),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"FAIL: no non-empty candidates generated. manifest={paths['manifest']}")
        return 1

    print(f"manifest: {paths['manifest']}")
    print(f"review: {board_path}")
    print(f"candidates: {len(report)}")
    for item in report:
        print(f"  - {item['slug']}: {item['candidate_rgba']} restore={item['restore_px']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
