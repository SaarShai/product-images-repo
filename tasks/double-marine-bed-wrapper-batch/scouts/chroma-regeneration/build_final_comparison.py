#!/usr/bin/env python3
"""Build source-aligned final comparison boards without issuing model calls."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("chroma_process", HERE / "process_candidates.py")
PROCESS = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(PROCESS)

OUT = PROCESS.OUT
SOURCE = PROCESS.SOURCE
ASSISTED_DIR = (
    OUT.parent.parent / "bg-assisted-v1" / "image14" / "assisted-r110-vitmatte"
)
ASSISTED_RGBA = ASSISTED_DIR / "image14-assisted-r110-rgba.png"
BENCHMARK_REPORTS = {
    "flux direct": OUT / "flux2-a" / "source-aligned-direct-key" / "frozen-benchmark-report.json",
    "flux hybrid": OUT / "flux2-a" / "source-payload-hybrid" / "frozen-benchmark-report.json",
    "nano direct": OUT / "nano-a" / "source-aligned-direct-key" / "frozen-benchmark-report.json",
    "nano hybrid": OUT / "nano-a" / "source-payload-hybrid" / "frozen-benchmark-report.json",
    "assisted r110": OUT / "assisted-r110-frozen-benchmark-report.json",
}
BACKGROUNDS = {
    "white": (255, 255, 255),
    "gray": (140, 140, 140),
    "black": (0, 0, 0),
    "magenta": (255, 0, 255),
}
ANNOTATIONS = HERE.parent.parent / "bg-benchmark" / "annotations" / "image14.json"
METHOD_LABELS = {
    "flux direct RGB": "F-direct",
    "flux source payload": "F-hybrid",
    "nano direct RGB": "N-direct",
    "nano source payload": "N-hybrid",
    "assisted r110": "r110",
}
PANEL_LABELS = {"source": "src", "white": "W", "gray": "G", "black": "K", "magenta": "M"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_rgba(path: Path) -> tuple[np.ndarray, np.ndarray]:
    rgba = np.asarray(Image.open(path).convert("RGBA"), dtype=np.uint8)
    return rgba[:, :, :3], rgba[:, :, 3].astype(np.float32) / 255.0


def registered_direct(candidate_id: str, source_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(Image.open(OUT / candidate_id / "raw.png").convert("RGB"), dtype=np.uint8)
    key = PROCESS.parse_hex("#00FF00")
    alpha, _ = PROCESS.key_alpha(raw, key)
    despilled, _ = PROCESS.despill(raw, alpha, key)
    raw_white = PROCESS.composite(despilled, alpha, (255, 255, 255))
    registered_rgb, registered_alpha, _ = PROCESS.register_analysis(
        source_rgb, raw_white, alpha, despilled
    )
    existing = np.asarray(
        Image.open(OUT / candidate_id / "registered-analysis.png").convert("RGB"),
        dtype=np.uint8,
    )
    regenerated = PROCESS.composite(registered_rgb, registered_alpha, (255, 255, 255))
    if not np.array_equal(regenerated, existing):
        raise RuntimeError(f"{candidate_id}: deterministic registration no longer matches stored analysis")
    return registered_rgb, registered_alpha


def fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    copy = image.convert("RGB")
    copy.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "#252525")
    canvas.paste(copy, ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
    return canvas


def build_board(
    source_rgb: np.ndarray,
    methods: dict[str, tuple[np.ndarray, np.ndarray]],
    box: tuple[int, int, int, int] | None,
    path: Path,
    title: str,
) -> None:
    font = ImageFont.load_default()
    names = ["source"] + list(BACKGROUNDS)
    if box is None:
        tile_size = (210, 373)
        label_height = 26
        row_height = tile_size[1] + label_height
        board = Image.new("RGB", (tile_size[0] * len(names), row_height * len(methods)), "#171717")
        draw = ImageDraw.Draw(board)
        source_image = Image.fromarray(source_rgb)
        for row, (method, (rgb, alpha)) in enumerate(methods.items()):
            panels = {"source": source_image}
            panels.update(
                {
                    name: Image.fromarray(PROCESS.composite(rgb, alpha, color))
                    for name, color in BACKGROUNDS.items()
                }
            )
            y = row * row_height
            for column, name in enumerate(names):
                x = column * tile_size[0]
                board.paste(fit(panels[name], tile_size), (x, y + label_height))
                draw.text(
                    (x + 4, y + 5),
                    f"{METHOD_LABELS[method]} | {PANEL_LABELS[name]}",
                    fill="white",
                    font=font,
                )
        draw.text((4, board.height - 14), title, fill="#bbbbbb", font=font)
    else:
        x0, y0, x1, y1 = box
        crop_width, crop_height = x1 - x0, y1 - y0
        tile_width = max(120, min(500, crop_width * 2))
        display_scale = tile_width / crop_width
        tile_size = (tile_width, max(1, round(crop_height * display_scale)))
        label_height = 25
        row_height = tile_size[1] + label_height
        board = Image.new("RGB", (tile_size[0] * len(names), row_height * len(methods)), "#171717")
        draw = ImageDraw.Draw(board)
        source_crop = Image.fromarray(source_rgb).crop(box).resize(tile_size, Image.Resampling.NEAREST)
        for row, (method, (rgb, alpha)) in enumerate(methods.items()):
            panels = {"source": source_crop}
            panels.update(
                {
                    name: Image.fromarray(PROCESS.composite(rgb, alpha, color))
                    .crop(box)
                    .resize(tile_size, Image.Resampling.NEAREST)
                    for name, color in BACKGROUNDS.items()
                }
            )
            y = row * row_height
            for column, name in enumerate(names):
                x = column * tile_size[0]
                board.paste(panels[name], (x, y + label_height))
                draw.text(
                    (x + 3, y + 5),
                    f"{METHOD_LABELS[method]} | {PANEL_LABELS[name]}",
                    fill="white",
                    font=font,
                )
    board.save(path, optimize=True)


def report_summary(path: Path) -> dict:
    report = json.loads(path.read_text())["reports"][0]
    return {
        "path": str(path),
        "sha256": sha256(path),
        "machine_pass": report["machine_pass"],
        "final_verdict": report["final_verdict"],
        "failure_codes": [item["code"] for item in report["failures"]],
        "straight_rgb_reconstruction": report["straight_rgb_reconstruction"],
    }


def save_source_aligned_direct(
    candidate_id: str, rgb: np.ndarray, alpha: np.ndarray
) -> Path:
    directory = OUT / candidate_id / "source-aligned-direct-key"
    directory.mkdir(exist_ok=True)
    alpha_u8 = np.clip(np.round(alpha * 255.0), 0, 255).astype(np.uint8)
    rgba_path = directory / "registered-keyed-rgba.png"
    Image.fromarray(np.dstack([rgb, alpha_u8])).save(rgba_path)
    composites = {}
    for name, background in BACKGROUNDS.items():
        path = directory / f"on-{name}.png"
        Image.fromarray(PROCESS.composite(rgb, alpha, background)).save(path)
        composites[name] = {"path": str(path), "sha256": sha256(path)}
    metrics = {
        "candidate_id": candidate_id,
        "architecture": "source-aligned direct keyed regenerated RGB and alpha",
        "analysis_only": True,
        "source_payload_used": False,
        "rgba": {"path": str(rgba_path), "sha256": sha256(rgba_path), "size_wh": [941, 1672]},
        "composites": composites,
    }
    (directory / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    return rgba_path


def main() -> None:
    source_rgb = np.asarray(Image.open(SOURCE).convert("RGB"), dtype=np.uint8)
    flux_direct = registered_direct("flux2-a", source_rgb)
    nano_direct = registered_direct("nano-a", source_rgb)
    save_source_aligned_direct("flux2-a", *flux_direct)
    save_source_aligned_direct("nano-a", *nano_direct)
    flux_hybrid = load_rgba(OUT / "flux2-a" / "source-payload-hybrid" / "source-payload-rgba.png")
    nano_hybrid = load_rgba(OUT / "nano-a" / "source-payload-hybrid" / "source-payload-rgba.png")
    assisted = load_rgba(ASSISTED_RGBA)
    methods = {
        "flux direct RGB": flux_direct,
        "flux source payload": flux_hybrid,
        "nano direct RGB": nano_direct,
        "nano source payload": nano_hybrid,
        "assisted r110": assisted,
    }

    artifacts: dict[str, dict[str, str]] = {}
    full_path = OUT / "final-method-comparison-full.png"
    build_board(
        source_rgb,
        methods,
        None,
        full_path,
        "Direct regenerated RGB versus source-payload hybrids versus assisted r110",
    )
    artifacts["full"] = {"path": str(full_path), "sha256": sha256(full_path)}
    for roi_name, spec in PROCESS.ROIS.items():
        box = PROCESS.roi_box(spec["center"], spec["size"], (source_rgb.shape[1], source_rgb.shape[0]))
        crop_path = OUT / f"final-method-comparison-crop-{roi_name}.png"
        build_board(source_rgb, methods, box, crop_path, f"source box={box}")
        artifacts[f"crop_{roi_name}"] = {"path": str(crop_path), "sha256": sha256(crop_path)}

    annotations = json.loads(ANNOTATIONS.read_text())
    benchmark_zones = {
        item["id"]: tuple(item["bbox"])
        for item in annotations["edge_probes"]
    }
    benchmark_zones.update(
        {
            item["id"]: tuple(item["bbox"])
            for item in annotations["human_review"]
            if item.get("kind") == "bbox"
        }
    )
    for zone_name, box in benchmark_zones.items():
        zone_path = OUT / f"final-benchmark-zone-{zone_name}.png"
        build_board(source_rgb, methods, box, zone_path, f"frozen benchmark source box={box}")
        artifacts[f"benchmark_zone_{zone_name}"] = {
            "path": str(zone_path),
            "sha256": sha256(zone_path),
        }

    summary = {
        "schema": "chroma-regeneration-final-comparison/v1",
        "source": {"path": str(SOURCE), "sha256": sha256(SOURCE), "size_wh": [941, 1672]},
        "methods": list(methods),
        "method_labels": METHOD_LABELS,
        "panel_labels": PANEL_LABELS,
        "backgrounds": BACKGROUNDS,
        "artifacts": artifacts,
        "frozen_benchmark": {
            name: report_summary(path) for name, path in BENCHMARK_REPORTS.items()
        },
        "interpretation": "All five frozen benchmark variants failed; boards are evidence, not approval.",
    }
    summary_path = OUT / "final-method-comparison.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    manifest_path = OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["source_payload_hybrid"]["status"] = "frozen_benchmark_rejected_not_promotable"
    manifest["final_evaluation"] = {
        "status": "complete_all_candidates_rejected",
        "evaluation_report": {
            "path": str(HERE / "EVALUATION.md"),
            "sha256": sha256(HERE / "EVALUATION.md"),
        },
        "comparison_summary": str(summary_path),
        "comparison_summary_sha256": sha256(summary_path),
        "artifacts": artifacts,
        "frozen_benchmark": summary["frozen_benchmark"],
        "requires_parent_vision_verdict": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(
        f"FINAL_COMPARISON_OK methods={len(methods)} "
        f"crops={len(PROCESS.ROIS)} benchmark_zones={len(benchmark_zones)}"
    )


if __name__ == "__main__":
    main()
