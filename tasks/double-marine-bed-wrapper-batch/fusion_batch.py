#!/usr/bin/env python3
"""Batch runner for the locked Tw250-erode1-defringe fusion path."""

from __future__ import annotations

import argparse
import gc
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from fusion_bg_removal import (
    bg_color_model,
    component_decisions,
    composite_on_bg,
    defringe_rgb,
    edge_metrics,
    erode_bool,
    fit_tile,
    flood_bg_mask,
    flood_intrusion_report,
    full_overlay_tile,
    get_font,
    luma_chroma,
    overlay_image,
    remove_small_fg,
    write_rgba,
)

Image.MAX_IMAGE_PIXELS = None


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/Images/finals"
)
OUT_DIR = REPO_ROOT / "Images/candidates/batch-fusion"
REVIEW_DIR = REPO_ROOT / "REVIEW/batch-fusion"
METRICS_PATH = OUT_DIR / "batch-fusion-metrics.json"

TW = 250
VARIANT = "erode1-defringe"
MIN_SPECK_AREA = 32
ERODE_ITERATIONS = 1
DEFRINGE_INNER_BAND_PX = 3
RESTORE_MIN_AREA = 64
TARGET_NUMBERS = tuple(f"{i:02d}" for i in range(1, 20) if i != 14)
EXCLUDED_NUMBERS = {"14", "20", "21", "22"}


def alpha_values(alpha: np.ndarray) -> list[int]:
    return [int(v) for v in np.unique(alpha)]


def target_sources() -> list[tuple[str, Path]]:
    grouped: dict[str, list[Path]] = {nn: [] for nn in TARGET_NUMBERS}
    for path in sorted(SOURCE_DIR.glob("[0-9][0-9]-*@x8-bg-removed.png")):
        nn = path.name[:2]
        if nn in EXCLUDED_NUMBERS:
            continue
        if nn in grouped:
            grouped[nn].append(path)

    missing = [nn for nn, paths in grouped.items() if not paths]
    duplicate = {nn: [str(p) for p in paths] for nn, paths in grouped.items() if len(paths) > 1}
    if missing or duplicate:
        raise RuntimeError(
            "target source mismatch: "
            f"missing={missing or 'none'} duplicate={duplicate or 'none'}"
        )
    return [(nn, grouped[nn][0]) for nn in TARGET_NUMBERS]


def output_path(nn: str) -> Path:
    return OUT_DIR / f"{nn}-fusion-Tw{TW}-{VARIANT}.png"


def review_path(nn: str) -> Path:
    return REVIEW_DIR / f"{nn}-review-sheet.jpg"


def crop_box_for_component(
    bbox_xywh: list[int],
    image_size: tuple[int, int],
    crop_size: int = 720,
) -> tuple[int, int, int, int]:
    x, y, w, h = bbox_xywh
    image_w, image_h = image_size
    crop_w = min(crop_size, image_w)
    crop_h = min(crop_size, image_h)
    cx = x + (w / 2.0)
    cy = y + (h / 2.0)
    x0 = int(round(cx - (crop_w / 2.0)))
    y0 = int(round(cy - (crop_h / 2.0)))
    x0 = max(0, min(x0, image_w - crop_w))
    y0 = max(0, min(y0, image_h - crop_h))
    return (x0, y0, x0 + crop_w, y0 + crop_h)


def restored_rois(
    decisions: list[dict[str, Any]],
    image_size: tuple[int, int],
) -> list[dict[str, Any]]:
    restored = [d for d in decisions if d.get("verdict") == "restore"]
    restored.sort(key=lambda d: int(d.get("area", 0)), reverse=True)
    rois = []
    for idx, decision in enumerate(restored[:3], start=1):
        bbox = [int(v) for v in decision["bbox_xywh"]]
        rois.append(
            {
                "rank": idx,
                "component_id": int(decision["component_id"]),
                "area": int(decision["area"]),
                "bbox_xywh": bbox,
                "crop_xyxy": list(crop_box_for_component(bbox, image_size)),
            }
        )
    return rois


def rgba_from_crop(rgb_crop: np.ndarray, mask_crop: np.ndarray) -> Image.Image:
    out = Image.fromarray(rgb_crop, "RGB").convert("RGBA")
    out.putalpha(Image.fromarray(mask_crop.astype(np.uint8) * 255, "L"))
    return out


def array_rgba_tile(
    rgb: np.ndarray,
    mask: np.ndarray,
    bg: tuple[int, int, int],
    size: tuple[int, int],
) -> Image.Image:
    h, w = mask.shape
    scale = min((size[0] - 12) / w, (size[1] - 12) / h)
    thumb_size = (max(1, int(w * scale)), max(1, int(h * scale)))
    small_rgb = Image.fromarray(rgb, "RGB").resize(thumb_size, Image.Resampling.LANCZOS)
    small_alpha = Image.fromarray(mask.astype(np.uint8) * 255, "L").resize(
        thumb_size, Image.Resampling.NEAREST
    )
    rgba = small_rgb.convert("RGBA")
    rgba.putalpha(small_alpha)
    comp = composite_on_bg(rgba, bg)
    tile = Image.new("RGB", size, bg)
    tile.paste(comp, ((size[0] - comp.width) // 2, (size[1] - comp.height) // 2))
    return tile


def make_review_sheet(
    *,
    nn: str,
    source_name: str,
    metric: dict[str, Any],
    rgb_variant: np.ndarray,
    output_mask: np.ndarray,
    restored: np.ndarray,
    kept_hole: np.ndarray,
    removed_fringe: np.ndarray,
    rois: list[dict[str, Any]],
    out_path: Path,
) -> None:
    font = get_font(24)
    small = get_font(18)
    width = 720 * 3
    header_h = 96
    full_h = 560
    roi_label_h = 34
    roi_h = 720
    footer_h = 34
    if not rois:
        roi_rows = [
            {
                "rank": 1,
                "component_id": None,
                "area": 0,
                "bbox_xywh": [0, 0, 0, 0],
                "crop_xyxy": [0, 0, min(720, rgb_variant.shape[1]), min(720, rgb_variant.shape[0])],
            }
        ]
    else:
        roi_rows = rois
    height = header_h + full_h + len(roi_rows) * (roi_label_h + roi_h) + footer_h

    sheet = Image.new("RGB", (width, height), (232, 232, 232))
    draw = ImageDraw.Draw(sheet)
    draw.rectangle((0, 0, width, header_h), fill=(255, 255, 255))
    draw.text(
        (14, 12),
        f"{nn}  Tw={TW}  {VARIANT}  {source_name}",
        fill=(0, 0, 0),
        font=font,
    )
    draw.text(
        (14, 52),
        (
            f"restored {metric['restored_components']} comps/{metric['restored_px']} px; "
            f"holes {metric['holes_open']}; flood_intrusion {metric['flood_intrusion_components']}; "
            f"fringe {metric['fringe_score']:.3f}"
        ),
        fill=(0, 0, 0),
        font=small,
    )

    full_tiles = (
        ("mid grey", array_rgba_tile(rgb_variant, output_mask, (128, 128, 128), (720, full_h))),
        ("black", array_rgba_tile(rgb_variant, output_mask, (0, 0, 0), (720, full_h))),
        (
            "decision overlay",
            full_overlay_tile(rgb_variant, restored, kept_hole, removed_fringe, (720, full_h)),
        ),
    )
    y = header_h
    for col, (label, tile) in enumerate(full_tiles):
        x = col * 720
        sheet.paste(tile, (x, y))
        draw.rectangle((x, y, x + 720, y + 30), fill=(255, 255, 255))
        draw.text((x + 10, y + 6), label, fill=(0, 0, 0), font=small)

    y += full_h
    for roi in roi_rows:
        x0, y0, x1, y1 = [int(v) for v in roi["crop_xyxy"]]
        draw.rectangle((0, y, width, y + roi_label_h), fill=(250, 250, 250))
        draw.text(
            (10, y + 7),
            (
                f"ROI {roi['rank']}: component={roi['component_id']} area={roi['area']} "
                f"crop=({x0},{y0},{x1},{y1})"
            ),
            fill=(0, 0, 0),
            font=small,
        )
        y += roi_label_h

        crop = rgba_from_crop(rgb_variant[y0:y1, x0:x1], output_mask[y0:y1, x0:x1])
        grey = fit_tile(composite_on_bg(crop, (128, 128, 128)), (720, roi_h), (128, 128, 128))
        black = fit_tile(composite_on_bg(crop, (0, 0, 0)), (720, roi_h), (0, 0, 0))
        overlay = fit_tile(
            overlay_image(
                rgb_variant[y0:y1, x0:x1],
                restored[y0:y1, x0:x1],
                kept_hole[y0:y1, x0:x1],
                removed_fringe[y0:y1, x0:x1],
            ),
            (720, roi_h),
            (245, 245, 245),
        )
        sheet.paste(grey, (0, y))
        sheet.paste(black, (720, y))
        sheet.paste(overlay, (1440, y))
        y += roi_h

    draw.rectangle((0, height - footer_h, width, height), fill=(255, 255, 255))
    draw.text(
        (10, height - 26),
        "overlay: restored=green, kept-hole=blue, removed-fringe=red",
        fill=(0, 0, 0),
        font=small,
    )
    sheet.save(out_path, quality=92)


def anomaly_flags(metric: dict[str, Any]) -> list[str]:
    flags = []
    if int(metric["flood_intrusion_components"]) > 0:
        flags.append("flood_intrusion_components>0")
    if int(metric["holes_open"]) == 0:
        flags.append("holes_open==0")
    ratio = float(metric["restored_px"]) / float(metric["image_px"])
    if ratio > 0.15:
        flags.append("restored_px>15%")
    if ratio < 0.0005:
        flags.append("restored_px<0.05%")
    return flags


def process_one(nn: str, source_path: Path, position: int, total: int) -> dict[str, Any]:
    out_path = output_path(nn)
    sheet_path = review_path(nn)
    print(f"[{position}/{total}] {nn}: {source_path.name}", flush=True)

    with Image.open(source_path) as im:
        src_rgba = im.convert("RGBA")
        image_size = src_rgba.size
        rgb = np.asarray(src_rgba.convert("RGB")).copy()
        source_alpha = np.asarray(src_rgba.getchannel("A")).copy()
    bria_fg = source_alpha >= 128

    luma, chroma = luma_chroma(rgb)
    flood_bg, flood_stats = flood_bg_mask(luma, chroma, TW)
    flood_stats["bg_color_model"] = bg_color_model(rgb, flood_bg)
    intrusion = flood_intrusion_report(flood_bg, bria_fg, luma, chroma)
    r_mask = (~flood_bg) & ~bria_fg
    restored, decisions, summary = component_decisions(r_mask, bria_fg, luma, chroma)
    final_mask, small_summary = remove_small_fg(bria_fg | restored, MIN_SPECK_AREA)
    output_mask = erode_bool(final_mask, ERODE_ITERATIONS)
    rgb_variant, defringe_px = defringe_rgb(rgb, output_mask, luma)
    kept_hole = r_mask & ~restored
    removed_fringe = final_mask & ~output_mask
    edge = edge_metrics(rgb_variant, output_mask, chroma, luma)
    rois = restored_rois(decisions, image_size)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        output_action = "skipped-existing"
    else:
        write_rgba(rgb_variant, output_mask, out_path)
        output_action = "wrote"
    if sheet_path.exists():
        review_action = "skipped-existing"
    else:
        make_review_sheet(
            nn=nn,
            source_name=source_path.name,
            metric={
                "restored_components": summary["restored_components"],
                "restored_px": summary["restored_px"],
                "holes_open": edge["holes_kept_open"],
                "flood_intrusion_components": intrusion["flooded_paint_like_components"],
                "fringe_score": edge["fringe_score"],
            },
            rgb_variant=rgb_variant,
            output_mask=output_mask,
            restored=restored,
            kept_hole=kept_hole,
            removed_fringe=removed_fringe,
            rois=rois,
            out_path=sheet_path,
        )
        review_action = "wrote"

    out_alpha_values = [0, 255] if bool(output_mask.any()) and bool((~output_mask).any()) else alpha_values(output_mask.astype(np.uint8) * 255)
    metric = {
        "nn": nn,
        "name": f"{nn}-fusion-Tw{TW}-{VARIANT}",
        "source_path": str(source_path),
        "source_name": source_path.name,
        "output_path": str(out_path),
        "review_sheet": str(sheet_path),
        "tw": TW,
        "variant": VARIANT,
        "near_white_rule": "luma>=250 AND chroma<=12",
        "restore_gate": "area>=64 AND touches_bria AND (median_chroma>10 OR median_luma<235)",
        "speck_removal_lt_px": MIN_SPECK_AREA,
        "erode_iterations": ERODE_ITERATIONS,
        "defringe_inner_band_px": DEFRINGE_INNER_BAND_PX,
        "source_width": int(image_size[0]),
        "source_height": int(image_size[1]),
        "output_width": int(image_size[0]),
        "output_height": int(image_size[1]),
        "image_px": int(image_size[0] * image_size[1]),
        "source_alpha_values_found": alpha_values(source_alpha),
        "alpha_values_found": out_alpha_values,
        "restored_components": int(summary["restored_components"]),
        "restored_px": int(summary["restored_px"]),
        "restored_ratio": float(summary["restored_px"]) / float(image_size[0] * image_size[1]),
        "candidate_components": int(summary["candidate_components"]),
        "kept_transparent_components": int(summary["kept_transparent_components"]),
        "kept_transparent_px": int(summary["kept_transparent_px"]),
        "holes_open": int(edge["holes_kept_open"]),
        "holes_open_px": int(edge["holes_kept_open_px"]),
        "flood_intrusion_components": int(intrusion["flooded_paint_like_components"]),
        "flood_intrusion_px": int(intrusion["flooded_paint_like_px"]),
        "flood_intrusion_component_samples": intrusion["components"],
        "fringe_score": edge["fringe_score"],
        "edge_luma_mean": edge["edge_luma_mean"],
        "interior_luma_mean": edge["interior_luma_mean"],
        "overcut_score": int(edge["overcut_score"]),
        "defringe_px": int(defringe_px),
        "small_fg_removed_components": int(small_summary["small_fg_removed_components"]),
        "small_fg_removed_px": int(small_summary["small_fg_removed_px"]),
        "near_white_px": int(flood_stats["near_white_px"]),
        "flood_bg_px": int(flood_stats["flood_bg_px"]),
        "bg_color_model": flood_stats["bg_color_model"],
        "review_rois": rois,
        "output_action": output_action,
        "review_action": review_action,
    }
    metric["anomaly_flags"] = anomaly_flags(metric)

    print(
        (
            f"[{position}/{total}] {nn}: output={output_action} review={review_action} "
            f"restored={metric['restored_components']}/{metric['restored_px']} "
            f"holes={metric['holes_open']} flood_intrusion={metric['flood_intrusion_components']} "
            f"fringe={metric['fringe_score']:.3f}"
        ),
        flush=True,
    )

    del (
        rgb,
        source_alpha,
        bria_fg,
        luma,
        chroma,
        flood_bg,
        r_mask,
        restored,
        final_mask,
        output_mask,
        rgb_variant,
        kept_hole,
        removed_fringe,
    )
    gc.collect()
    return metric


def write_metrics(metrics: list[dict[str, Any]]) -> None:
    doc = {
        "source_dir": str(SOURCE_DIR),
        "output_dir": str(OUT_DIR),
        "review_dir": str(REVIEW_DIR),
        "tw": TW,
        "variant": VARIANT,
        "target_numbers": list(TARGET_NUMBERS),
        "excluded_numbers": sorted(EXCLUDED_NUMBERS),
        "metrics": metrics,
        "anomalies": [
            {"nn": m["nn"], "flags": m["anomaly_flags"]}
            for m in metrics
            if m["anomaly_flags"]
        ],
    }
    METRICS_PATH.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print(f"metrics_json: {METRICS_PATH}", flush=True)


def print_metrics_table(metrics: list[dict[str, Any]]) -> None:
    print("METRICS TABLE", flush=True)
    print(
        "nn\trestored_components\trestored_px\trestored_pct\tholes_open\t"
        "flood_intrusion_components\tfringe_score\talpha_values",
        flush=True,
    )
    for m in metrics:
        print(
            f"{m['nn']}\t{m['restored_components']}\t{m['restored_px']}\t"
            f"{m['restored_ratio'] * 100:.4f}%\t{m['holes_open']}\t"
            f"{m['flood_intrusion_components']}\t{m['fringe_score']:.3f}\t"
            f"{m['alpha_values_found']}",
            flush=True,
        )


def run_batch() -> None:
    sources = target_sources()
    metrics = []
    print(f"source_dir: {SOURCE_DIR}", flush=True)
    print(f"output_dir: {OUT_DIR}", flush=True)
    print(f"review_dir: {REVIEW_DIR}", flush=True)
    print(f"targets: {', '.join(nn for nn, _path in sources)}", flush=True)
    for idx, (nn, source_path) in enumerate(sources, start=1):
        metrics.append(process_one(nn, source_path, idx, len(sources)))
    write_metrics(metrics)
    print_metrics_table(metrics)


def verify_outputs() -> int:
    sources = target_sources()
    errors: list[str] = []
    print(f"VERIFY target_count={len(sources)}", flush=True)
    print(f"VERIFY metrics_json_exists={METRICS_PATH.exists()} path={METRICS_PATH}", flush=True)
    pngs = sorted(OUT_DIR.glob("[0-9][0-9]-fusion-Tw250-erode1-defringe.png"))
    sheets = sorted(REVIEW_DIR.glob("[0-9][0-9]-review-sheet.jpg"))
    print(f"VERIFY png_count={len(pngs)} expected=18 dir={OUT_DIR}", flush=True)
    print(f"VERIFY review_sheet_count={len(sheets)} expected=18 dir={REVIEW_DIR}", flush=True)
    if len(pngs) != len(sources):
        errors.append(f"png_count={len(pngs)} expected={len(sources)}")
    if len(sheets) != len(sources):
        errors.append(f"review_sheet_count={len(sheets)} expected={len(sources)}")
    if not METRICS_PATH.exists():
        errors.append(f"missing_metrics_json={METRICS_PATH}")

    for nn, source_path in sources:
        out = output_path(nn)
        sheet = review_path(nn)
        source_size = None
        with Image.open(source_path) as src:
            source_size = src.size
        exists = out.exists()
        sheet_exists = sheet.exists()
        if not exists:
            errors.append(f"{nn}: missing output {out}")
            print(
                f"VERIFY {nn}: exists=no source_dims={source_size} review_exists={sheet_exists}",
                flush=True,
            )
            continue
        with Image.open(out) as im:
            output_size = im.size
            mode = im.mode
            if "A" not in im.getbands():
                vals: list[int] = []
            else:
                vals = alpha_values(np.asarray(im.getchannel("A")))
        dims_match = output_size == source_size
        alpha_ok = vals == [0, 255]
        if not dims_match:
            errors.append(f"{nn}: dims {output_size} != source {source_size}")
        if not alpha_ok:
            errors.append(f"{nn}: alpha_values {vals} != [0, 255]")
        if not sheet_exists:
            errors.append(f"{nn}: missing review sheet {sheet}")
        print(
            (
                f"VERIFY {nn}: exists=yes mode={mode} dims={output_size} "
                f"source_dims={source_size} dims_match={dims_match} "
                f"alpha_values={vals} alpha_ok={alpha_ok} "
                f"review_exists={sheet_exists}"
            ),
            flush=True,
        )

    if errors:
        print("VERIFY status=FAIL", flush=True)
        for error in errors:
            print(f"VERIFY error={error}", flush=True)
        return 1
    print("VERIFY status=PASS", flush=True)
    return 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        raise SystemExit(verify_outputs())
    run_batch()


if __name__ == "__main__":
    main()
