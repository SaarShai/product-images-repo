#!/usr/bin/env python3
"""Batch x8 upscale + hard-alpha background removal for double Marine Bed Wrapper.

This is intentionally scoped to the approved project lane:
Real-ESRGAN x4plus -> BRIA hard180 mask -> colored-margin restore -> x16/Lanczos
RGB downsample to x8 -> binary x8 alpha transfer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
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


REPO_ROOT = Path(__file__).resolve().parents[2]
REALESRGAN = REPO_ROOT / "tasks/marine-pod-upscale/tools/realesrgan-full/realesrgan-ncnn-vulkan"
REALESRGAN_MODELS = REPO_ROOT / "tasks/marine-pod-upscale/tools/realesrgan-full/models"


@dataclass
class Paths:
    source_dir: Path
    candidates_dir: Path
    final_dir: Path
    x4_rgb_dir: Path
    x4_mask_dir: Path
    review_dir: Path
    tmp_dir: Path
    manifest: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--candidate-dir", type=Path)
    parser.add_argument("--final-dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--keep-x16", action="store_true")
    parser.add_argument("--hard-threshold", type=int, default=180)
    parser.add_argument("--restore-saturation", type=int, default=22)
    parser.add_argument("--restore-value-max", type=int, default=210)
    parser.add_argument("--restore-dilate", type=int, default=5)
    parser.add_argument("--restore-min-component-px", type=int, default=256)
    parser.add_argument("--restore-max-pct", type=float, default=0.35)
    parser.add_argument("--restore-max-components", type=int, default=180)
    parser.add_argument("--tiny-component-px", type=int, default=4)
    parser.add_argument("--skip-upscale", action="store_true")
    return parser.parse_args()


def safe_slug(stem: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    slug = re.sub(r"_+", "_", slug)
    return slug[:140] or "image"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inventory(source_dir: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(source_dir.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_file():
            continue
        try:
            with Image.open(path) as im:
                im.verify()
            out.append(path)
        except Exception:
            continue
    return out


def ensure_paths(args: argparse.Namespace) -> Paths:
    source_dir = args.source_dir.expanduser().resolve()
    image_root = source_dir / "Images"
    candidates_dir = (args.candidate_dir or (image_root / "candidates/batch-x8-hard180")).resolve()
    final_dir = (args.final_dir or (image_root / "finals")).resolve()
    manifest = (args.manifest or (final_dir / "batch-manifest.json")).resolve()
    paths = Paths(
        source_dir=source_dir,
        candidates_dir=candidates_dir,
        final_dir=final_dir,
        x4_rgb_dir=candidates_dir / "x4-rgb",
        x4_mask_dir=candidates_dir / "x4-hard180",
        review_dir=final_dir / "review",
        tmp_dir=candidates_dir / "tmp",
        manifest=manifest,
    )
    for p in (
        paths.candidates_dir,
        paths.final_dir,
        paths.x4_rgb_dir,
        paths.x4_mask_dir,
        paths.review_dir,
        paths.tmp_dir,
    ):
        p.mkdir(parents=True, exist_ok=True)
    return paths


def run_cmd(cmd: list[str]) -> None:
    print("+ " + " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True)


def run_realesrgan(src: Path, out: Path, scale: int = 4) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    run_cmd(
        [
            REALESRGAN,
            "-i",
            src,
            "-o",
            out,
            "-n",
            "realesrgan-x4plus",
            "-m",
            REALESRGAN_MODELS,
            "-s",
            str(scale),
            "-t",
            "512",
            "-f",
            "png",
        ]
    )


def rgb_to_sv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    arr = rgb.astype(np.float32) / 255.0
    mx = arr.max(axis=2)
    mn = arr.min(axis=2)
    delta = mx - mn
    sat = np.zeros_like(mx)
    nz = mx > 0
    sat[nz] = delta[nz] / mx[nz]
    return (sat * 255.0).astype(np.uint8), (mx * 255.0).astype(np.uint8)


def remove_tiny_foreground(mask: np.ndarray, min_area: int) -> tuple[np.ndarray, int, int]:
    if min_area <= 0:
        return mask, 0, 0
    labels, count = ndi.label(mask)
    if count == 0:
        return mask, 0, 0
    areas = np.bincount(labels.ravel())
    remove_labels = np.where((areas > 0) & (areas < min_area))[0]
    remove_labels = remove_labels[remove_labels != 0]
    if len(remove_labels) == 0:
        return mask, 0, 0
    remove = np.isin(labels, remove_labels)
    out = mask.copy()
    out[remove] = False
    return out, int(remove.sum()), int(len(remove_labels))


def alpha_metrics(mask: np.ndarray) -> dict[str, Any]:
    total = int(mask.size)
    opaque = int(mask.sum())
    transparent = total - opaque
    labels, components = ndi.label(mask)
    areas = np.bincount(labels.ravel()) if components else np.array([], dtype=np.int64)
    small_lt64 = int(((areas[1:] < 64) & (areas[1:] > 0)).sum()) if areas.size else 0
    return {
        "transparent_pct": transparent / total * 100.0,
        "opaque_pct": opaque / total * 100.0,
        "semi_pct": 0.0,
        "foreground_components": int(components),
        "small_foreground_components_lt64": small_lt64,
    }


def colored_margin_restore(
    rgb: np.ndarray,
    mask: np.ndarray,
    saturation_threshold: int,
    value_max: int,
    dilate_px: int,
    min_component_px: int,
    max_pct: float,
    max_components: int,
) -> tuple[np.ndarray, dict[str, Any], np.ndarray]:
    sat, val = rgb_to_sv(rgb)
    colored = (sat >= saturation_threshold) | (
        (val <= value_max) & (sat >= max(8, saturation_threshold // 2))
    )
    near_foreground = ndi.binary_dilation(mask, iterations=dilate_px)
    candidates = (~mask) & near_foreground & colored
    labels, raw_count = ndi.label(candidates)
    areas = np.bincount(labels.ravel()) if raw_count else np.array([], dtype=np.int64)
    if raw_count:
        keep_labels = np.where(areas >= min_component_px)[0]
        keep_labels = keep_labels[keep_labels != 0]
        restore = np.isin(labels, keep_labels)
        count = int(len(keep_labels))
    else:
        restore = candidates
        count = 0
    restore_px = int(restore.sum())
    restore_pct = restore_px / mask.size * 100.0
    applied = restore_px > 0 and restore_pct <= max_pct and count <= max_components
    out = mask.copy()
    if applied:
        out[restore] = True
    else:
        restore = np.zeros_like(mask, dtype=bool)
    metrics = {
        "applied": bool(applied),
        "candidate_px": restore_px,
        "candidate_pct": restore_pct,
        "candidate_components": int(count),
        "raw_candidate_components": int(raw_count),
        "min_component_px": min_component_px,
        "restored_px": int(restore.sum()),
        "restore_dilate_px": dilate_px,
        "restore_saturation_threshold": saturation_threshold,
        "restore_value_max": value_max,
        "guard_max_pct": max_pct,
        "guard_max_components": max_components,
        "component_area_max": int(areas[1:].max()) if areas.size > 1 else 0,
    }
    return out, metrics, restore


def bria_mask_hard180(x4_rgb: Path, args: argparse.Namespace) -> tuple[Image.Image, dict[str, Any], np.ndarray]:
    from rembg import new_session, remove

    session = bria_mask_hard180.session
    if session is None:
        session = new_session("bria-rmbg")
        bria_mask_hard180.session = session

    rgb_img = Image.open(x4_rgb).convert("RGB")
    raw = remove(rgb_img.convert("RGBA"), session=session)
    raw_alpha = np.asarray(raw.getchannel("A"))
    mask = raw_alpha >= args.hard_threshold
    mask, removed_px, removed_components = remove_tiny_foreground(mask, args.tiny_component_px)
    rgb = np.asarray(rgb_img)
    repaired, restore_metrics, restore_mask = colored_margin_restore(
        rgb=rgb,
        mask=mask,
        saturation_threshold=args.restore_saturation,
        value_max=args.restore_value_max,
        dilate_px=args.restore_dilate,
        min_component_px=args.restore_min_component_px,
        max_pct=args.restore_max_pct,
        max_components=args.restore_max_components,
    )

    metrics = alpha_metrics(repaired)
    metrics.update(
        {
            "hard_threshold": args.hard_threshold,
            "tiny_components_removed_px": removed_px,
            "tiny_components_removed": removed_components,
            "restore": restore_metrics,
            "raw_alpha_min": int(raw_alpha.min()),
            "raw_alpha_max": int(raw_alpha.max()),
        }
    )
    alpha = Image.fromarray(np.where(repaired, 255, 0).astype(np.uint8), "L")
    rgba = rgb_img.convert("RGBA")
    rgba.putalpha(alpha)
    return rgba, metrics, restore_mask


bria_mask_hard180.session = None


def save_restore_overlay(rgb_path: Path, restore_mask: np.ndarray, out_path: Path) -> None:
    rgb = Image.open(rgb_path).convert("RGB")
    base = rgb.resize((max(1, rgb.width // 2), max(1, rgb.height // 2)), Image.Resampling.LANCZOS).convert("RGBA")
    mask_img = Image.fromarray((restore_mask.astype(np.uint8) * 180), "L").resize(base.size, Image.Resampling.NEAREST)
    overlay = Image.new("RGBA", base.size, (0, 255, 0, 0))
    overlay.putalpha(mask_img)
    base.alpha_composite(overlay)
    base.convert("RGB").save(out_path, quality=92)


def resize_rgb_from_x16(x16: Path, size: tuple[int, int]) -> Image.Image:
    with Image.open(x16) as im:
        return im.convert("RGB").resize(size, Image.Resampling.LANCZOS)


def apply_x8_alpha(x8_rgb: Image.Image, x4_rgba: Image.Image, final_path: Path) -> None:
    alpha_x8 = x4_rgba.getchannel("A").resize(x8_rgb.size, Image.Resampling.NEAREST)
    final = x8_rgb.convert("RGBA")
    final.putalpha(alpha_x8.point(lambda p: 255 if p >= 128 else 0))
    final.save(final_path, optimize=True)


def final_alpha_metrics(path: Path) -> tuple[int, int, dict[str, Any]]:
    with Image.open(path) as final_img:
        width, height = final_img.size
        alpha = np.asarray(final_img.convert("RGBA").getchannel("A"))
    total_px = int(alpha.size)
    semi = int(((alpha > 0) & (alpha < 255)).sum())
    opaque = int((alpha == 255).sum())
    metrics = {
        "transparent_pct": (total_px - opaque - semi) / total_px * 100.0,
        "opaque_pct": opaque / total_px * 100.0,
        "semi_pct": semi / total_px * 100.0,
        "semi_px": semi,
    }
    return width, height, metrics


def make_gray_preview(rgba_path: Path, out_path: Path, max_side: int = 1800) -> None:
    im = Image.open(rgba_path).convert("RGBA")
    scale = min(1.0, max_side / max(im.size))
    if scale < 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.Resampling.LANCZOS)
    bg = Image.new("RGBA", im.size, (96, 96, 96, 255))
    bg.alpha_composite(im)
    bg.convert("RGB").save(out_path, quality=92)


def tile_label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    x, y = xy
    draw.rectangle((x, y, x + 640, y + 26), fill=(255, 255, 255))
    draw.text((x + 6, y + 4), text[:74], fill=(0, 0, 0), font=font)


def make_contact_sheet(entries: list[dict[str, Any]], out_path: Path, background: tuple[int, int, int], cols: int = 4) -> None:
    thumbs: list[tuple[str, Image.Image]] = []
    for entry in entries:
        final = Path(entry["final_path"])
        if not final.exists():
            continue
        im = Image.open(final).convert("RGBA")
        tile_w, tile_h = 480, 480
        scale = min((tile_w - 20) / im.width, (tile_h - 50) / im.height)
        small = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.Resampling.LANCZOS)
        bg = Image.new("RGBA", (tile_w, tile_h), (*background, 255))
        bg.alpha_composite(small, ((tile_w - small.width) // 2, 40 + (tile_h - 50 - small.height) // 2))
        thumbs.append((entry["slug"], bg.convert("RGB")))
    if not thumbs:
        return
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 480, rows * 480), (240, 240, 240))
    draw = ImageDraw.Draw(sheet)
    for idx, (label, img) in enumerate(thumbs):
        x = (idx % cols) * 480
        y = (idx // cols) * 480
        sheet.paste(img, (x, y))
        tile_label(draw, (x, y), label)
    sheet.save(out_path, quality=92)


def process_one(src: Path, index: int, total: int, paths: Paths, args: argparse.Namespace) -> dict[str, Any]:
    slug = f"{index:02d}-{safe_slug(src.stem)}"
    final_path = paths.final_dir / f"{slug}@x8-bg-removed.png"
    x4_rgb = paths.x4_rgb_dir / f"{slug}@x4-rgb.png"
    x4_rgba = paths.x4_mask_dir / f"{slug}@x4-hard180-colorrestore.png"
    restore_overlay = paths.x4_mask_dir / f"{slug}@x4-colorrestore-overlay.jpg"
    gray_preview = paths.review_dir / f"{slug}@x8-gray-preview.jpg"
    x16_tmp = paths.tmp_dir / f"{slug}@x16-rgb.png"

    started = time.time()
    with Image.open(src) as src_img:
        src_w, src_h = src_img.size
        src_mode = src_img.mode
    entry: dict[str, Any] = {
        "index": index,
        "slug": slug,
        "source": str(src),
        "source_path": str(src),
        "source_name": src.name,
        "source_sha256": sha256_file(src),
        "source_width": src_w,
        "source_height": src_h,
        "source_mode": src_mode,
        "eligible": True,
        "final": str(final_path),
        "final_path": str(final_path),
        "x4_rgb_path": str(x4_rgb),
        "x4_cutout_path": str(x4_rgba),
        "restore_overlay_path": str(restore_overlay),
        "gray_preview_path": str(gray_preview),
        "allow_semi_transparent_alpha": False,
    }

    if final_path.exists() and not args.force:
        if not args.keep_x16:
            x16_tmp.unlink(missing_ok=True)
        entry["status"] = "skipped_existing"
        entry["final_width"], entry["final_height"], entry["alpha_metrics_x8"] = final_alpha_metrics(final_path)
        entry["final_sha256"] = sha256_file(final_path)
        if not gray_preview.exists():
            make_gray_preview(final_path, gray_preview)
        return entry

    print(f"\n[{index}/{total}] {src.name}", flush=True)
    if not x4_rgb.exists() or args.force:
        if args.skip_upscale:
            raise FileNotFoundError(f"missing x4 RGB and --skip-upscale set: {x4_rgb}")
        run_realesrgan(src, x4_rgb, scale=4)
    else:
        print(f"reuse {x4_rgb}", flush=True)

    x4_cutout, mask_metrics, restore_mask = bria_mask_hard180(x4_rgb, args)
    x4_cutout.save(x4_rgba, optimize=True)
    save_restore_overlay(x4_rgb, restore_mask, restore_overlay)
    entry["mask_metrics_x4"] = mask_metrics

    if not args.skip_upscale:
        if x16_tmp.exists() and args.force:
            x16_tmp.unlink()
        if not x16_tmp.exists():
            run_realesrgan(x4_rgb, x16_tmp, scale=4)
    if not x16_tmp.exists():
        raise FileNotFoundError(f"missing x16 transient: {x16_tmp}")
    x8_rgb = resize_rgb_from_x16(x16_tmp, (src_w * 8, src_h * 8))
    apply_x8_alpha(x8_rgb, x4_cutout, final_path)
    make_gray_preview(final_path, gray_preview)
    if not args.keep_x16:
        x16_tmp.unlink(missing_ok=True)

    entry["final_width"], entry["final_height"], entry["alpha_metrics_x8"] = final_alpha_metrics(final_path)
    entry["status"] = "ok"
    entry["elapsed_sec"] = round(time.time() - started, 2)
    entry["final_sha256"] = sha256_file(final_path)
    print(f"wrote {final_path}", flush=True)
    return entry


def write_manifest(paths: Paths, entries: list[dict[str, Any]], started_at: float) -> None:
    manifest = {
        "workflow": "x4 Real-ESRGAN x4plus -> BRIA hard180 -> colored-margin restore -> x16/Lanczos RGB downsample -> x8 binary mask transfer",
        "generated_at_unix": int(time.time()),
        "elapsed_sec": round(time.time() - started_at, 2),
        "source_dir": str(paths.source_dir),
        "candidate_dir": str(paths.candidates_dir),
        "final_dir": str(paths.final_dir),
        "entries": entries,
    }
    tmp = paths.manifest.with_suffix(paths.manifest.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp.replace(paths.manifest)


def main() -> int:
    args = parse_args()
    paths = ensure_paths(args)
    if not REALESRGAN.exists():
        print(f"missing Real-ESRGAN binary: {REALESRGAN}", file=sys.stderr)
        return 2
    if not REALESRGAN_MODELS.exists():
        print(f"missing Real-ESRGAN models dir: {REALESRGAN_MODELS}", file=sys.stderr)
        return 2

    sources = inventory(paths.source_dir)
    sources = sources[args.start_index - 1 :]
    if args.limit:
        sources = sources[: args.limit]
    if not sources:
        print("no eligible source images")
        return 1

    started_at = time.time()
    entries: list[dict[str, Any]] = []
    total = len(sources)
    try:
        for offset, src in enumerate(sources, start=args.start_index):
            entry = process_one(src, offset, args.start_index + total - 1, paths, args)
            entries.append(entry)
            write_manifest(paths, entries, started_at)
    finally:
        if entries:
            write_manifest(paths, entries, started_at)

    make_contact_sheet(entries, paths.review_dir / "contact-sheet-gray.jpg", (96, 96, 96))
    make_contact_sheet(entries, paths.review_dir / "contact-sheet-white.jpg", (255, 255, 255))
    make_contact_sheet(entries, paths.review_dir / "contact-sheet-black.jpg", (0, 0, 0))
    make_contact_sheet(entries, paths.review_dir / "contact-sheet-magenta.jpg", (255, 0, 255))
    write_manifest(paths, entries, started_at)
    print(f"\nmanifest: {paths.manifest}")
    print(f"review: {paths.review_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
