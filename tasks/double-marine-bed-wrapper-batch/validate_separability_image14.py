#!/usr/bin/env python3
"""Measure color statistics to validate paint-vs-paper separation in BRIA overcut regions.

On real watercolor marine image14, verify that color statistics (chroma, luma, distance
from background model) can distinguish restored pale coral from actual background paper.

Output: colored diagnostic PNG + statistics table.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NamedTuple

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi


class ComponentStats(NamedTuple):
    component_id: int
    area: int
    median_chroma: float
    median_luma: float
    mean_distance_from_bg: float
    perimeter_touching_bria: float
    bbox: tuple[int, int, int, int]
    classification: str


# Configuration
PRODUCT_DIR = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
SOURCE_RGB = PRODUCT_DIR / "ChatGPT Image Jul 7, 2026, 11_22_35 AM.png"
BRIA_RGBA = PRODUCT_DIR / (
    "Images/candidates/image14-research/raw/"
    "01-bria-rmbg-alpha-matting-hard180.png"
)
REVIEW_DIR = Path("/Users/za/Documents/product images repo/REVIEW/image14-bg")


def ensure_paths() -> None:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    for path in (SOURCE_RGB, BRIA_RGBA):
        if not path.exists():
            raise FileNotFoundError(f"Required input missing: {path}")


def load_images() -> tuple[np.ndarray, np.ndarray]:
    """Load source RGB and BRIA alpha, handling dimension mismatch."""
    src_img = Image.open(SOURCE_RGB).convert("RGB")
    src_rgb = np.asarray(src_img)
    src_h, src_w = src_rgb.shape[:2]

    bria_img = Image.open(BRIA_RGBA).convert("RGBA")
    bria_rgba = np.asarray(bria_img)
    bria_h, bria_w = bria_rgba.shape[:2]

    if (bria_h, bria_w) != (src_h, src_w):
        print(
            f"Dimension mismatch: source {src_h}x{src_w}, BRIA {bria_h}x{bria_w}",
            file=sys.stderr,
        )
        print(f"Resizing BRIA alpha to match source...", file=sys.stderr)
        bria_alpha_ch = Image.fromarray(bria_rgba[:, :, 3], "L")
        bria_alpha_ch = bria_alpha_ch.resize((src_w, src_h), Image.Resampling.NEAREST)
        bria_alpha = np.asarray(bria_alpha_ch)
    else:
        bria_alpha = bria_rgba[:, :, 3]

    return src_rgb, bria_alpha


def rgb_to_chroma_luma(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute chroma (max-min) and luma (relative brightness 0..255)."""
    rgb_f = rgb.astype(np.float32) / 255.0
    mx = rgb_f.max(axis=2)
    mn = rgb_f.min(axis=2)
    chroma = (mx - mn) * 255.0
    luma = mx * 255.0
    return chroma.astype(np.uint8), luma.astype(np.uint8)


def build_flood_bg(rgb: np.ndarray) -> np.ndarray:
    """Flood-fill near-white background connected to border.

    Near-white: luma >= 245 AND chroma <= 12.
    Returns binary mask: True = background.
    """
    chroma, luma = rgb_to_chroma_luma(rgb)
    near_white = (luma >= 245) & (chroma <= 12)

    # Label connected components
    labels, count = ndi.label(near_white)

    # Find components touching border
    border_ids = set()
    if labels.shape[0] > 0:
        border_ids.update(labels[0, :].tolist())
        border_ids.update(labels[-1, :].tolist())
    if labels.shape[1] > 0:
        border_ids.update(labels[:, 0].tolist())
        border_ids.update(labels[:, -1].tolist())
    border_ids.discard(0)

    # Keep only border-connected components
    flood_bg = np.isin(labels, list(border_ids))
    return flood_bg


def compute_background_model(
    rgb: np.ndarray, flood_bg: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Compute per-channel mean and std of background pixels."""
    bg_pixels = rgb[flood_bg]
    if bg_pixels.shape[0] == 0:
        return np.array([255.0, 255.0, 255.0]), np.array([1.0, 1.0, 1.0])

    mean = bg_pixels.mean(axis=0)
    std = bg_pixels.std(axis=0)
    return mean, std


def distance_from_bg_model(
    rgb: np.ndarray, mean: np.ndarray, std: np.ndarray
) -> np.ndarray:
    """Compute Mahalanobis-like distance from background color model."""
    safe_std = np.maximum(std, 1e-3)
    normalized = (rgb.astype(np.float32) - mean[None, None, :]) / safe_std[None, None, :]
    distance = np.sqrt((normalized ** 2).sum(axis=2))
    return distance


def extract_overcut_components(
    rgb: np.ndarray, flood_bg: np.ndarray, bria_alpha: np.ndarray, min_area: int = 32
) -> tuple[np.ndarray, dict[int, ComponentStats]]:
    """Extract components of overcut regions (FloodFG AND NOT BriaFG)."""
    bria_fg = bria_alpha >= 128
    flood_fg = ~flood_bg

    # Overcut: regions that flood-fill classified as foreground but BRIA removed
    overcut = flood_fg & ~bria_fg

    # Label 8-connected components
    labels, count = ndi.label(overcut)
    areas = np.bincount(labels.ravel()) if count else np.array([], dtype=np.int64)

    components: dict[int, ComponentStats] = {}
    chroma, luma = rgb_to_chroma_luma(rgb)
    mean, std = compute_background_model(rgb, flood_bg)
    dist = distance_from_bg_model(rgb, mean, std)

    for comp_id in range(1, count + 1):
        mask = labels == comp_id
        area = int(mask.sum())

        if area < min_area:
            continue

        # Collect stats
        chroma_vals = chroma[mask]
        luma_vals = luma[mask]
        dist_vals = dist[mask]

        median_chroma = float(np.median(chroma_vals))
        median_luma = float(np.median(luma_vals))
        mean_distance = float(dist_vals.mean())

        # Fraction of perimeter touching BRIA foreground
        dilation = ndi.binary_dilation(mask, iterations=1)
        perimeter = dilation & ~mask
        perimeter_on_bria = perimeter & bria_fg
        perimeter_ratio = (
            float(perimeter_on_bria.sum() / max(1, perimeter.sum()))
            if perimeter.sum() > 0
            else 0.0
        )

        # Bounding box
        rows, cols = np.where(mask)
        bbox = (int(rows.min()), int(cols.min()), int(rows.max()), int(cols.max()))

        # Heuristic classification: PAINT if high chroma OR low luma, else PAPER
        if median_chroma > 10 or median_luma < 235:
            classification = "PAINT"
        else:
            classification = "PAPER"

        components[comp_id] = ComponentStats(
            component_id=comp_id,
            area=area,
            median_chroma=median_chroma,
            median_luma=median_luma,
            mean_distance_from_bg=mean_distance,
            perimeter_touching_bria=perimeter_ratio,
            bbox=bbox,
            classification=classification,
        )

    return labels, components


def extract_holes_in_bria_fg(
    rgb: np.ndarray, flood_bg: np.ndarray, bria_alpha: np.ndarray, min_area: int = 16
) -> dict[int, ComponentStats]:
    """Extract true holes: background components INSIDE BriaFG."""
    bria_fg = bria_alpha >= 128

    # Background inside BRIA foreground: near-white but NOT connected to border
    chroma, luma = rgb_to_chroma_luma(rgb)
    near_white = (luma >= 245) & (chroma <= 12)
    inside_bria = near_white & bria_fg

    # Label and find only non-border components
    labels, count = ndi.label(inside_bria)
    areas = np.bincount(labels.ravel()) if count else np.array([], dtype=np.int64)

    # Find border-connected IDs (from flood_bg)
    border_bg_ids = set(labels[flood_bg].tolist())
    border_bg_ids.discard(0)

    holes: dict[int, ComponentStats] = {}
    mean, std = compute_background_model(rgb, flood_bg)
    dist = distance_from_bg_model(rgb, mean, std)

    for comp_id in range(1, count + 1):
        if comp_id in border_bg_ids:
            continue

        mask = labels == comp_id
        area = int(mask.sum())

        if area < min_area:
            continue

        # Stats for hole
        chroma_vals = chroma[mask]
        luma_vals = luma[mask]
        dist_vals = dist[mask]

        median_chroma = float(np.median(chroma_vals))
        median_luma = float(np.median(luma_vals))
        mean_distance = float(dist_vals.mean())

        rows, cols = np.where(mask)
        bbox = (int(rows.min()), int(cols.min()), int(rows.max()), int(cols.max()))

        # Holes should be PAPER-like by definition
        if median_chroma > 10 or median_luma < 235:
            classification = "PAINT_HOLE"
        else:
            classification = "PAPER_HOLE"

        holes[comp_id] = ComponentStats(
            component_id=comp_id,
            area=area,
            median_chroma=median_chroma,
            median_luma=median_luma,
            mean_distance_from_bg=mean_distance,
            perimeter_touching_bria=0.0,
            bbox=bbox,
            classification=classification,
        )

    return holes


def create_diagnostic_png(
    rgb: np.ndarray,
    overcut_labels: np.ndarray,
    components: dict[int, ComponentStats],
    holes: dict[int, ComponentStats],
) -> Path:
    """Create colored diagnostic PNG showing classification."""
    # Start with source RGB
    out = rgb.copy()
    h, w = out.shape[:2]

    # Color overcut components: green=PAINT, red=PAPER
    for comp_id, stats in components.items():
        mask = overcut_labels == comp_id
        if stats.classification == "PAINT":
            out[mask] = [0, 255, 0]  # Green
        else:
            out[mask] = [255, 0, 0]  # Red

    # Holes are trickier to visualize (they're inside BRIA FG)
    # Mark hole regions with blue border outline
    for hole_id, stats in holes.items():
        r0, c0, r1, c1 = stats.bbox
        # Draw a blue border around hole bbox
        out[r0:r1, c0, :] = [0, 0, 255]
        out[r0:r1, c1, :] = [0, 0, 255]
        out[r0, c0:c1, :] = [0, 0, 255]
        out[r1, c0:c1, :] = [0, 0, 255]

    result_img = Image.fromarray(out.astype(np.uint8), "RGB")
    out_path = REVIEW_DIR / "separability-diagnostic.png"
    result_img.save(out_path)
    return out_path


def format_stats_table(
    components: dict[int, ComponentStats], holes: dict[int, ComponentStats]
) -> str:
    """Format statistics table for reporting."""
    lines = []
    lines.append("=" * 110)
    lines.append("OVERCUT COMPONENTS (R = FloodFG AND NOT BriaFG, area >= 32)")
    lines.append("=" * 110)
    lines.append(
        f"{'ID':>3} {'Area':>8} {'Chroma':>8} {'Luma':>8} {'Distance':>10} {'Perimeter':>10} {'Class':>8} {'BBox':>30}"
    )
    lines.append("-" * 110)

    sorted_components = sorted(components.items(), key=lambda x: x[1].area, reverse=True)
    for comp_id, stats in sorted_components[:30]:
        bbox_str = f"({stats.bbox[0]},{stats.bbox[1]})-({stats.bbox[2]},{stats.bbox[3]})"
        lines.append(
            f"{stats.component_id:3d} {stats.area:8d} {stats.median_chroma:8.1f} {stats.median_luma:8.1f} "
            f"{stats.mean_distance_from_bg:10.2f} {stats.perimeter_touching_bria:10.2%} {stats.classification:>8} {bbox_str:>30}"
        )

    lines.append("")
    lines.append("=" * 110)
    lines.append("TRUE HOLES (non-border-connected near-white inside BriaFG)")
    lines.append("=" * 110)
    lines.append(
        f"{'ID':>3} {'Area':>8} {'Chroma':>8} {'Luma':>8} {'Distance':>10} {'Class':>15} {'BBox':>30}"
    )
    lines.append("-" * 110)

    sorted_holes = sorted(holes.items(), key=lambda x: x[1].area, reverse=True)
    for hole_id, stats in sorted_holes[:20]:
        bbox_str = f"({stats.bbox[0]},{stats.bbox[1]})-({stats.bbox[2]},{stats.bbox[3]})"
        lines.append(
            f"{stats.component_id:3d} {stats.area:8d} {stats.median_chroma:8.1f} {stats.median_luma:8.1f} "
            f"{stats.mean_distance_from_bg:10.2f} {stats.classification:>15} {bbox_str:>30}"
        )

    return "\n".join(lines)


def analyze_separation(
    components: dict[int, ComponentStats],
) -> tuple[bool, str]:
    """Analyze whether color stats cleanly separate PAINT from PAPER."""
    paint_comps = [s for s in components.values() if s.classification == "PAINT"]
    paper_comps = [s for s in components.values() if s.classification == "PAPER"]

    if not paint_comps or not paper_comps:
        return False, (
            f"Insufficient data: {len(paint_comps)} PAINT, {len(paper_comps)} PAPER."
        )

    # Check chroma separation
    paint_chroma = [c.median_chroma for c in paint_comps]
    paper_chroma = [c.median_chroma for c in paper_comps]
    paint_chroma_min = min(paint_chroma)
    paper_chroma_max = max(paper_chroma)

    # Check luma separation
    paint_luma = [c.median_luma for c in paint_comps]
    paper_luma = [c.median_luma for c in paper_comps]
    paint_luma_min = min(paint_luma)
    paper_luma_max = max(paper_luma)

    sep_msg = f"Chroma: PAINT {paint_chroma_min:.1f}..{max(paint_chroma):.1f}, PAPER {min(paper_chroma):.1f}..{paper_chroma_max:.1f}; "
    sep_msg += f"Luma: PAINT {paint_luma_min:.1f}..{max(paint_luma):.1f}, PAPER {min(paper_luma):.1f}..{paper_luma_max:.1f}"

    # Heuristic: separation is "clean" if thresholds don't overlap
    clean = (paint_chroma_min > paper_chroma_max) or (paint_luma_min < paper_luma_max)

    margin = ""
    if paint_chroma_min > paper_chroma_max:
        margin = f"Chroma margin: {paint_chroma_min - paper_chroma_max:.1f}"
    elif paint_luma_min < paper_luma_max:
        margin = f"Luma margin: {paper_luma_max - paint_luma_min:.1f}"

    return clean, sep_msg + (f" [{margin}]" if margin else " [OVERLAP]")


def main() -> int:
    print("Validating paint-vs-paper separability for image14 BRIA overcuts", flush=True)
    print(f"Source: {SOURCE_RGB}", flush=True)
    print(f"BRIA:   {BRIA_RGBA}", flush=True)

    ensure_paths()

    # Load images
    print("Loading images...", flush=True)
    src_rgb, bria_alpha = load_images()
    print(f"Source RGB: {src_rgb.shape}, BRIA alpha: {bria_alpha.shape}", flush=True)

    # Build background model via flood-fill
    print("Building flood-fill background model...", flush=True)
    flood_bg = build_flood_bg(src_rgb)
    bg_px = int(flood_bg.sum())
    total_px = int(flood_bg.size)
    print(
        f"Background pixels: {bg_px:,} / {total_px:,} ({bg_px/total_px*100:.1f}%)",
        flush=True,
    )

    # Extract overcut components
    print("Extracting overcut regions...", flush=True)
    overcut_labels, components = extract_overcut_components(src_rgb, flood_bg, bria_alpha)
    print(f"Found {len(components)} overcut components (area >= 32)", flush=True)

    # Extract true holes
    print("Extracting true holes inside BriaFG...", flush=True)
    holes = extract_holes_in_bria_fg(src_rgb, flood_bg, bria_alpha)
    print(f"Found {len(holes)} true hole components (area >= 16)", flush=True)

    # Analyze separation
    is_clean, separation_analysis = analyze_separation(components)
    print(f"\nSeparation: {'CLEAN' if is_clean else 'DIRTY'}", flush=True)
    print(separation_analysis, flush=True)

    # Create diagnostic PNG
    print(f"Creating diagnostic PNG...", flush=True)
    diag_path = create_diagnostic_png(src_rgb, overcut_labels, components, holes)
    print(f"Diagnostic PNG: {diag_path}", flush=True)

    # Print statistics table
    stats_table = format_stats_table(components, holes)
    print("\n" + stats_table, flush=True)

    # Summary
    print("\n" + "=" * 110)
    print("SUMMARY", flush=True)
    print("=" * 110)
    paint_count = sum(1 for c in components.values() if c.classification == "PAINT")
    paper_count = sum(
        1 for c in components.values() if c.classification == "PAPER"
    )
    holes_paper = sum(1 for h in holes.values() if h.classification == "PAPER_HOLE")
    holes_paint = sum(1 for h in holes.values() if h.classification == "PAINT_HOLE")

    print(f"Overcut components: {paint_count} PAINT, {paper_count} PAPER", flush=True)
    print(
        f"True holes: {holes_paper} PAPER_HOLE, {holes_paint} PAINT_HOLE",
        flush=True,
    )
    print(f"\nSource file: {SOURCE_RGB}", flush=True)
    print(f"Diagnostic: {diag_path}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
