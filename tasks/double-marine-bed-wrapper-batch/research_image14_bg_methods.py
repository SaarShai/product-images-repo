#!/usr/bin/env python3
"""Research-backed background-removal candidates for double Marine image 14.

This is intentionally one-image-only. It compares model/matting approaches for
the image-14 white-edge / wrong-cutout problem and writes review artifacts under
the product folder's Images/candidates/image14-research/ directory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None


PRODUCT_DIR = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
SOURCE = PRODUCT_DIR / "ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
FINAL = PRODUCT_DIR / (
    "Images/finals/"
    "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x8-bg-removed.png"
)
X4_RGB = PRODUCT_DIR / (
    "Images/candidates/batch-x8-hard180/x4-rgb/"
    "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
)
RAW_BRIA_ALPHA = PRODUCT_DIR / (
    "Images/candidates/image14-repair/raw/"
    "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-bria-raw-alpha.png"
)
OUT_ROOT = PRODUCT_DIR / "Images/candidates/image14-research"


@dataclass(frozen=True)
class CandidateSpec:
    slug: str
    label: str
    kind: str
    model: str | None = None
    matting: bool = False
    threshold: int = 180


CANDIDATES = [
    CandidateSpec(
        "01-bria-rmbg-alpha-matting-hard180",
        "BRIA RMBG + rembg alpha matting + hard180",
        "rembg",
        "bria-rmbg",
        True,
        180,
    ),
    CandidateSpec(
        "02-birefnet-general-hard180",
        "BiRefNet general + hard180",
        "rembg",
        "birefnet-general",
        False,
        180,
    ),
    CandidateSpec(
        "03-birefnet-hrsod-hard180",
        "BiRefNet HRSOD + hard180",
        "rembg",
        "birefnet-hrsod",
        False,
        180,
    ),
    CandidateSpec(
        "04-pymatting-cf-trimap-hard180",
        "PyMatting closed-form trimap + hard180",
        "pymatting",
        None,
        False,
        180,
    ),
    CandidateSpec(
        "05-bria-matting-remove-white-matte-hard180",
        "BRIA alpha matte + remove-white-matte foreground colors + hard180",
        "white_matte",
        "bria-rmbg",
        True,
        180,
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--methods",
        nargs="*",
        default=[c.slug for c in CANDIDATES],
        help="Candidate slugs to run. Default: all.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--roi-count", type=int, default=8)
    parser.add_argument("--crop", type=int, default=720)
    parser.add_argument(
        "--skip-render",
        action="store_true",
        help="Only generate raw alpha/intermediate metrics; do not write full x8 PNGs.",
    )
    return parser.parse_args()


def ensure_inputs() -> None:
    missing = [p for p in (SOURCE, FINAL, X4_RGB, RAW_BRIA_ALPHA) if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n" + "\n".join(str(p) for p in missing))
    for sub in ("raw", "candidates", "review", "diagnostics"):
        (OUT_ROOT / sub).mkdir(parents=True, exist_ok=True)


def get_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def rgba_on_bg(path: Path, bg: tuple[int, int, int], size: tuple[int, int] | None = None) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    if size is not None:
        im = im.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", im.size, (*bg, 255))
    canvas.alpha_composite(im)
    return canvas.convert("RGB")


def rgb_to_sv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    arr = rgb.astype(np.float32) / 255.0
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    sat = np.zeros_like(mx)
    nz = mx > 0
    sat[nz] = (mx[nz] - mn[nz]) / mx[nz]
    return sat, mx


def harden_alpha(alpha: np.ndarray, threshold: int) -> np.ndarray:
    return alpha >= threshold


def remove_tiny(mask: np.ndarray, min_area: int = 6) -> np.ndarray:
    labels, count = ndi.label(mask)
    if count == 0:
        return mask
    areas = np.bincount(labels.ravel())
    small = np.where((areas > 0) & (areas < min_area))[0]
    small = small[small != 0]
    if len(small) == 0:
        return mask
    out = mask.copy()
    out[np.isin(labels, small)] = False
    return out


def decontaminate_boundary_rgb(
    rgb: np.ndarray, mask: np.ndarray, width: int = 5
) -> tuple[np.ndarray, np.ndarray]:
    """Replace near-white fringe pixels with nearest non-white interior color."""
    sat, val = rgb_to_sv(rgb)
    spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    whiteish = (val >= 0.91) & (sat <= 0.16) & (spread <= 38)
    dist_to_bg = ndi.distance_transform_edt(mask)
    boundary = mask & (dist_to_bg <= width)
    replace = boundary & whiteish
    if not replace.any():
        return rgb.copy(), replace

    interior = mask & (dist_to_bg > width + 1) & (~whiteish | (sat > 0.10) | (val < 0.88))
    if interior.sum() < 32:
        interior = mask & (dist_to_bg > width + 1)
    if interior.sum() < 32:
        return rgb.copy(), replace

    _, nearest = ndi.distance_transform_edt(~interior, return_indices=True)
    out = rgb.copy()
    yy, xx = nearest
    out[replace] = rgb[yy[replace], xx[replace]]
    return out, replace


def alpha_metrics(alpha: np.ndarray, raw_alpha: np.ndarray | None = None) -> dict[str, Any]:
    mask = alpha > 0
    semi = (alpha > 0) & (alpha < 255)
    boundary = ndi.binary_dilation(mask, iterations=1) & ~ndi.binary_erosion(mask, iterations=1)
    rgb = np.asarray(Image.open(X4_RGB).convert("RGB"))
    sat, val = rgb_to_sv(rgb)
    spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    whiteish = (val >= 0.94) & (sat <= 0.16) & (spread <= 38)
    unsafe_halo = boundary & whiteish

    bg = ~mask
    bg_labels, bg_count = ndi.label(bg)
    border_ids = set(bg_labels[0, :].tolist())
    border_ids.update(bg_labels[-1, :].tolist())
    border_ids.update(bg_labels[:, 0].tolist())
    border_ids.update(bg_labels[:, -1].tolist())
    border_ids.discard(0)
    bg_areas = np.bincount(bg_labels.ravel()) if bg_count else np.array([], dtype=np.int64)
    interior_areas = [
        int(area)
        for i, area in enumerate(bg_areas)
        if i != 0 and i not in border_ids and area >= 16
    ]
    interior_areas.sort(reverse=True)

    metrics: dict[str, Any] = {
        "size": [int(alpha.shape[1]), int(alpha.shape[0])],
        "transparent_pct": float((~mask).mean() * 100.0),
        "opaque_pct": float((alpha == 255).mean() * 100.0),
        "semi_pct": float(semi.mean() * 100.0),
        "semi_px": int(semi.sum()),
        "boundary_px": int(boundary.sum()),
        "unsafe_white_boundary_px": int(unsafe_halo.sum()),
        "unsafe_white_boundary_ratio": float(unsafe_halo.sum() / max(1, boundary.sum())),
        "interior_transparent_components_ge16": int(len(interior_areas)),
        "top_interior_transparent_component_px": interior_areas[:8],
    }
    if raw_alpha is not None:
        raw = raw_alpha
        metrics.update(
            {
                "low_conf_inside_px": int((mask & (raw < 64)).sum()),
                "missed_confidence_px": int(((~mask) & (raw > 220)).sum()),
                "low_conf_inside_ratio": float((mask & (raw < 64)).sum() / max(1, mask.sum())),
                "missed_confidence_ratio": float(((~mask) & (raw > 220)).sum() / max(1, (~mask).sum())),
            }
        )
    return metrics


def rembg_alpha(spec: CandidateSpec) -> tuple[np.ndarray, Path]:
    from rembg import new_session, remove

    raw_path = OUT_ROOT / "raw" / f"{spec.slug}.png"
    if raw_path.exists():
        return np.asarray(Image.open(raw_path).convert("RGBA").getchannel("A")), raw_path

    session = new_session(spec.model)
    img = Image.open(X4_RGB).convert("RGBA")
    kwargs: dict[str, Any] = {"session": session}
    if spec.matting:
        kwargs.update(
            {
                "alpha_matting": True,
                "alpha_matting_foreground_threshold": 240,
                "alpha_matting_background_threshold": 10,
                "alpha_matting_erode_size": 10,
            }
        )
    out = remove(img, **kwargs).convert("RGBA")
    out.save(raw_path)
    return np.asarray(out.getchannel("A")), raw_path


def border_connected_white_bg(rgb: np.ndarray, thresh: int = 238, spread_limit: int = 28) -> np.ndarray:
    mn = rgb.min(axis=2)
    spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    whiteish = (mn >= thresh) & (spread <= spread_limit)
    labels, _ = ndi.label(whiteish)
    border_ids = set(labels[0, :].tolist())
    border_ids.update(labels[-1, :].tolist())
    border_ids.update(labels[:, 0].tolist())
    border_ids.update(labels[:, -1].tolist())
    border_ids.discard(0)
    return np.isin(labels, list(border_ids))


def pymatting_alpha(spec: CandidateSpec) -> tuple[np.ndarray, Path]:
    from pymatting import estimate_alpha_cf

    raw_path = OUT_ROOT / "raw" / f"{spec.slug}-alpha.png"
    if raw_path.exists():
        return np.asarray(Image.open(raw_path).convert("L")), raw_path

    src = Image.open(SOURCE).convert("RGB")
    raw4 = Image.open(RAW_BRIA_ALPHA).convert("L")
    raw1 = raw4.resize(src.size, Image.Resampling.LANCZOS)
    raw = np.asarray(raw1)
    rgb = np.asarray(src)
    border_bg = border_connected_white_bg(rgb)

    fg_seed = raw >= 245
    fg_seed = ndi.binary_erosion(fg_seed, iterations=1)
    bg_seed = border_bg & (raw <= 24)

    unknown = np.ones(raw.shape, dtype=bool)
    unknown[fg_seed] = False
    unknown[bg_seed] = False

    trimap = np.full(raw.shape, 0.5, dtype=np.float64)
    trimap[bg_seed] = 0.0
    trimap[fg_seed] = 1.0

    image = rgb.astype(np.float64) / 255.0
    alpha = estimate_alpha_cf(
        image,
        trimap,
        cg_kwargs={"maxiter": 320, "rtol": 1e-5},
    )
    alpha = np.clip(alpha, 0, 1)
    alpha_img = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    alpha4 = alpha_img.resize(Image.open(X4_RGB).size, Image.Resampling.LANCZOS)
    alpha4.save(raw_path)

    trimap_img = Image.fromarray((trimap * 255).astype(np.uint8), "L")
    trimap_img.save(OUT_ROOT / "diagnostics" / f"{spec.slug}-trimap-source.png")
    return np.asarray(alpha4), raw_path


def write_candidate(spec: CandidateSpec, alpha4_soft: np.ndarray, raw_path: Path) -> dict[str, Any]:
    rgb4 = np.asarray(Image.open(X4_RGB).convert("RGB"))
    raw_reference = np.asarray(Image.open(RAW_BRIA_ALPHA).convert("L"))

    mask = harden_alpha(alpha4_soft, spec.threshold)
    mask = remove_tiny(mask)
    alpha4 = np.where(mask, 255, 0).astype(np.uint8)
    rgb4_clean, replaced = decontaminate_boundary_rgb(rgb4, mask)

    alpha4_path = OUT_ROOT / "diagnostics" / f"{spec.slug}-alpha4-hard.png"
    replace_path = OUT_ROOT / "diagnostics" / f"{spec.slug}-defringe-replaced-mask.png"
    Image.fromarray(alpha4, "L").save(alpha4_path)
    Image.fromarray((replaced.astype(np.uint8) * 255), "L").save(replace_path)

    final_path = OUT_ROOT / "candidates" / f"14-{spec.slug}.png"
    base_rgb = Image.open(FINAL).convert("RGB")
    edge_rgb = Image.fromarray(rgb4_clean, "RGB").resize(base_rgb.size, Image.Resampling.LANCZOS)
    edge_mask = Image.fromarray((replaced.astype(np.uint8) * 255), "L").resize(
        base_rgb.size, Image.Resampling.NEAREST
    )
    base_rgb.paste(edge_rgb, (0, 0), edge_mask)
    alpha8 = Image.fromarray(alpha4, "L").resize(base_rgb.size, Image.Resampling.LANCZOS)
    alpha8 = alpha8.point(lambda p: 255 if p >= 128 else 0)
    out = base_rgb.convert("RGBA")
    out.putalpha(alpha8)
    out.save(final_path, optimize=True)

    preview_path = OUT_ROOT / "review" / f"14-{spec.slug}-full-gray-preview.jpg"
    preview = rgba_on_bg(final_path, (96, 96, 96))
    preview.thumbnail((1200, 2200), Image.Resampling.LANCZOS)
    preview.save(preview_path, quality=92)

    metrics = alpha_metrics(alpha4, raw_reference)
    metrics.update(
        {
            "slug": spec.slug,
            "label": spec.label,
            "kind": spec.kind,
            "model": spec.model,
            "threshold": spec.threshold,
            "raw_path": str(raw_path),
            "alpha4_hard_path": str(alpha4_path),
            "defringe_replaced_mask_path": str(replace_path),
            "final_path": str(final_path),
            "preview_path": str(preview_path),
            "defringe_replaced_px": int(replaced.sum()),
        }
    )
    return metrics


def write_white_matte_candidate(spec: CandidateSpec, alpha4_soft: np.ndarray, raw_path: Path) -> dict[str, Any]:
    """Use the alpha equation C = aF + (1-a)W to remove a white matte."""
    rgb4 = np.asarray(Image.open(X4_RGB).convert("RGB"))
    raw_reference = np.asarray(Image.open(RAW_BRIA_ALPHA).convert("L"))
    alpha_f = np.clip(alpha4_soft.astype(np.float32) / 255.0, 0.0, 1.0)
    rgb_f = rgb4.astype(np.float32) / 255.0
    safe_a = np.maximum(alpha_f, 1.0 / 255.0)

    fg = (rgb_f - (1.0 - safe_a[..., None])) / safe_a[..., None]
    fg = np.clip(fg, 0.0, 1.0)
    fg_u8 = (fg * 255.0 + 0.5).astype(np.uint8)

    mask = harden_alpha(alpha4_soft, spec.threshold)
    mask = remove_tiny(mask)
    alpha4 = np.where(mask, 255, 0).astype(np.uint8)
    sat, val = rgb_to_sv(rgb4)
    spread = rgb4.max(axis=2).astype(np.int16) - rgb4.min(axis=2).astype(np.int16)
    dist_to_bg = ndi.distance_transform_edt(mask)
    whiteish = (val >= 0.88) & (sat <= 0.22) & (spread <= 56)
    replace = mask & ((alpha4_soft < 252) | ((dist_to_bg <= 7) & whiteish))

    alpha4_path = OUT_ROOT / "diagnostics" / f"{spec.slug}-alpha4-hard.png"
    replace_path = OUT_ROOT / "diagnostics" / f"{spec.slug}-remove-white-matte-replaced-mask.png"
    Image.fromarray(alpha4, "L").save(alpha4_path)
    Image.fromarray((replace.astype(np.uint8) * 255), "L").save(replace_path)

    final_path = OUT_ROOT / "candidates" / f"14-{spec.slug}.png"
    base_rgb = Image.open(FINAL).convert("RGB")
    edge_rgb = Image.fromarray(fg_u8, "RGB").resize(base_rgb.size, Image.Resampling.LANCZOS)
    edge_mask = Image.fromarray((replace.astype(np.uint8) * 255), "L").resize(
        base_rgb.size, Image.Resampling.NEAREST
    )
    base_rgb.paste(edge_rgb, (0, 0), edge_mask)
    alpha8 = Image.fromarray(alpha4, "L").resize(base_rgb.size, Image.Resampling.LANCZOS)
    alpha8 = alpha8.point(lambda p: 255 if p >= 128 else 0)
    out = base_rgb.convert("RGBA")
    out.putalpha(alpha8)
    out.save(final_path, optimize=True)

    preview_path = OUT_ROOT / "review" / f"14-{spec.slug}-full-gray-preview.jpg"
    preview = rgba_on_bg(final_path, (96, 96, 96))
    preview.thumbnail((1200, 2200), Image.Resampling.LANCZOS)
    preview.save(preview_path, quality=92)

    metrics = alpha_metrics(alpha4, raw_reference)
    metrics.update(
        {
            "slug": spec.slug,
            "label": spec.label,
            "kind": spec.kind,
            "model": spec.model,
            "threshold": spec.threshold,
            "raw_path": str(raw_path),
            "alpha4_hard_path": str(alpha4_path),
            "defringe_replaced_mask_path": str(replace_path),
            "final_path": str(final_path),
            "preview_path": str(preview_path),
            "remove_white_matte_replaced_px": int(replace.sum()),
        }
    )
    return metrics


def current_defect_rois(crop_size: int, limit: int) -> list[tuple[int, int, int, int]]:
    im = Image.open(FINAL).convert("RGBA")
    alpha = np.asarray(im.getchannel("A"))
    rgb = np.asarray(im.convert("RGB"))
    raw4 = Image.open(RAW_BRIA_ALPHA).convert("L")
    raw8 = np.asarray(raw4.resize(im.size, Image.Resampling.BILINEAR))

    mask = alpha > 0
    sat, val = rgb_to_sv(rgb)
    spread = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)
    boundary = ndi.binary_dilation(mask, iterations=1) & ~ndi.binary_erosion(mask, iterations=1)
    whiteish = (val >= 0.94) & (sat <= 0.18) & (spread <= 44)
    defect = boundary & whiteish
    defect |= mask & (raw8 < 64)
    defect |= (~mask) & (raw8 > 220)

    labels, count = ndi.label(defect)
    slices = ndi.find_objects(labels)
    scored: list[tuple[int, int, int, int, int]] = []
    for idx, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        area = int((labels[sl] == idx).sum())
        if area < 120:
            continue
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        scored.append((area, x0, y0, x1, y1))
    scored.sort(reverse=True)

    rois: list[tuple[int, int, int, int]] = []
    w, h = im.size
    for _area, x0, y0, x1, y1 in scored:
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        half = crop_size // 2
        rx0 = max(0, min(w - crop_size, cx - half))
        ry0 = max(0, min(h - crop_size, cy - half))
        roi = (rx0, ry0, rx0 + crop_size, ry0 + crop_size)
        if any(abs(roi[0] - old[0]) < crop_size // 2 and abs(roi[1] - old[1]) < crop_size // 2 for old in rois):
            continue
        rois.append(roi)
        if len(rois) >= limit:
            break
    return rois


def make_review_board(entries: list[dict[str, Any]], rois: list[tuple[int, int, int, int]], crop_size: int) -> Path:
    current = {
        "slug": "00-current-final",
        "final_path": str(FINAL),
        "label": "Current rejected final",
    }
    columns = [current] + entries
    tile = 360
    header = 48
    label_h = 34
    board = Image.new("RGB", (len(columns) * tile, header + len(rois) * (tile + label_h)), (232, 232, 232))
    draw = ImageDraw.Draw(board)
    font = get_font(17)
    small = get_font(14)

    for col, entry in enumerate(columns):
        x = col * tile
        draw.rectangle((x, 0, x + tile, header), fill=(255, 255, 255))
        draw.text((x + 8, 8), entry["slug"][:32], fill=(0, 0, 0), font=font)

    for row, roi in enumerate(rois):
        y = header + row * (tile + label_h)
        draw.rectangle((0, y, len(columns) * tile, y + label_h), fill=(250, 250, 250))
        draw.text((8, y + 8), f"ROI {row + 1}: x={roi[0]} y={roi[1]} size={crop_size}", fill=(0, 0, 0), font=small)
        for col, entry in enumerate(columns):
            x = col * tile
            crop = rgba_on_bg(Path(entry["final_path"]), (96, 96, 96)).crop(roi)
            crop.thumbnail((tile, tile), Image.Resampling.LANCZOS)
            tile_img = Image.new("RGB", (tile, tile), (96, 96, 96))
            tile_img.paste(crop, ((tile - crop.width) // 2, (tile - crop.height) // 2))
            board.paste(tile_img, (x, y + label_h))

    out = OUT_ROOT / "review" / "14-image14-research-roi-comparison-board.jpg"
    board.save(out, quality=94)
    return out


def make_alpha_overlay(entries: list[dict[str, Any]]) -> Path:
    cols = len(entries)
    tile_w, tile_h = 420, 680
    board = Image.new("RGB", (cols * tile_w, tile_h), (245, 245, 245))
    draw = ImageDraw.Draw(board)
    font = get_font(16)
    for col, entry in enumerate(entries):
        alpha = Image.open(entry["alpha4_hard_path"]).convert("L")
        alpha.thumbnail((tile_w - 24, tile_h - 56), Image.Resampling.NEAREST)
        canvas = Image.new("RGB", (tile_w, tile_h), (245, 245, 245))
        canvas.paste(alpha.convert("RGB"), ((tile_w - alpha.width) // 2, 44))
        board.paste(canvas, (col * tile_w, 0))
        draw.text((col * tile_w + 8, 10), entry["slug"][:38], fill=(0, 0, 0), font=font)
    out = OUT_ROOT / "review" / "14-image14-alpha-mask-contact-sheet.jpg"
    board.save(out, quality=92)
    return out


def run_candidate(spec: CandidateSpec) -> dict[str, Any]:
    started = time.time()
    if spec.kind == "rembg":
        alpha, raw_path = rembg_alpha(spec)
    elif spec.kind == "pymatting":
        alpha, raw_path = pymatting_alpha(spec)
    elif spec.kind == "white_matte":
        alpha, raw_path = rembg_alpha(spec)
        entry = write_white_matte_candidate(spec, alpha, raw_path)
        entry["elapsed_sec"] = round(time.time() - started, 2)
        return entry
    else:
        raise ValueError(f"unknown candidate kind: {spec.kind}")
    entry = write_candidate(spec, alpha, raw_path)
    entry["elapsed_sec"] = round(time.time() - started, 2)
    return entry


def main() -> int:
    args = parse_args()
    ensure_inputs()
    wanted = set(args.methods)
    specs = [c for c in CANDIDATES if c.slug in wanted]
    unknown = wanted - {c.slug for c in CANDIDATES}
    if unknown:
        raise SystemExit(f"Unknown methods: {sorted(unknown)}")

    manifest_path = OUT_ROOT / "manifest.json"
    entries: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for spec in specs:
        final_path = OUT_ROOT / "candidates" / f"14-{spec.slug}.png"
        if final_path.exists() and not args.force:
            print(f"reuse {final_path}", flush=True)
            alpha_path = OUT_ROOT / "diagnostics" / f"{spec.slug}-alpha4-hard.png"
            replace_path = OUT_ROOT / "diagnostics" / f"{spec.slug}-defringe-replaced-mask.png"
            alpha4 = np.asarray(Image.open(alpha_path).convert("L"))
            entry = alpha_metrics(alpha4, np.asarray(Image.open(RAW_BRIA_ALPHA).convert("L")))
            entry.update(
                {
                    "slug": spec.slug,
                    "label": spec.label,
                    "kind": spec.kind,
                    "model": spec.model,
                    "threshold": spec.threshold,
                    "alpha4_hard_path": str(alpha_path),
                    "defringe_replaced_mask_path": str(replace_path),
                    "final_path": str(final_path),
                    "preview_path": str(OUT_ROOT / "review" / f"14-{spec.slug}-full-gray-preview.jpg"),
                }
            )
            entries.append(entry)
            continue
        print(f"\n== {spec.slug}: {spec.label} ==", flush=True)
        try:
            entries.append(run_candidate(spec))
        except Exception as exc:
            errors.append({"slug": spec.slug, "error": f"{type(exc).__name__}: {exc}"})
            print(f"ERROR {spec.slug}: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)

    rois = current_defect_rois(args.crop, args.roi_count)
    roi_board = make_review_board(entries, rois, args.crop) if entries else None
    alpha_board = make_alpha_overlay(entries) if entries else None

    manifest = {
        "source": str(SOURCE),
        "current_final": str(FINAL),
        "x4_rgb": str(X4_RGB),
        "raw_bria_alpha": str(RAW_BRIA_ALPHA),
        "out_root": str(OUT_ROOT),
        "research_basis": [
            "rembg model A/B harness with alpha-matting support",
            "BiRefNet/BRIA model comparison",
            "trimap alpha matting via PyMatting",
            "Photoshop-style defringe: replace near-white boundary pixels with nearest interior color",
        ],
        "roi_board": str(roi_board) if roi_board else None,
        "alpha_board": str(alpha_board) if alpha_board else None,
        "rois_xyxy": [list(r) for r in rois],
        "entries": entries,
        "errors": errors,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nmanifest: {manifest_path}")
    if roi_board:
        print(f"roi_board: {roi_board}")
    if alpha_board:
        print(f"alpha_board: {alpha_board}")
    if errors:
        print(f"errors: {errors}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
