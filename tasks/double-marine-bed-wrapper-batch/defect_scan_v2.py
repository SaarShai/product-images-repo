#!/usr/bin/env python3
"""
Fast full-resolution defect scanner for background-removed PNG.
Optimized for large images with many small artifacts.
"""

import argparse
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import scipy.ndimage as ndi
from scipy.ndimage import label, find_objects

Image.MAX_IMAGE_PIXELS = None

def load_image(path, mode="RGBA"):
    img = Image.open(path)
    if img.mode != mode:
        img = img.convert(mode)
    return np.array(img, dtype=np.uint8)

def get_border_connected_mask_fast(alpha, max_iter=10):
    """Find border-connected transparent pixels (alpha==0)."""
    transparent = (alpha == 0)
    border_mask = np.zeros_like(transparent, dtype=bool)
    border_mask[0, :] = transparent[0, :]
    border_mask[-1, :] = transparent[-1, :]
    border_mask[:, 0] = transparent[:, 0]
    border_mask[:, -1] = transparent[:, -1]
    
    for _ in range(max_iter):
        old_count = border_mask.sum()
        border_mask = ndi.binary_dilation(border_mask, iterations=1) & transparent
        if border_mask.sum() == old_count:
            break
    
    return border_mask

def detect_cutout_defects(result_rgba, source_rgb):
    """Detect wrong cutouts: suspicious transparent pixels."""
    print("  Building BG color model...", file=sys.stderr)
    alpha = result_rgba[:, :, 3]
    transparent = (alpha == 0)
    
    border_connected = get_border_connected_mask_fast(alpha, max_iter=10)
    if border_connected.sum() == 0:
        return [], ((255, 255, 255), (0, 0, 0))
    
    bg_pixels = source_rgb[border_connected]
    bg_mean = bg_pixels.mean(axis=0)
    bg_std = bg_pixels.std(axis=0)
    bg_model = (bg_mean, bg_std)
    
    print(f"    BG model: mean={bg_mean.astype(int)}, std={bg_std.round(1)}", file=sys.stderr)
    print(f"    Finding suspicious pixels (>3σ from BG)...", file=sys.stderr)
    
    # Mark suspicious: ALL 3 channels must be >3σ from mean
    suspicious = np.ones(transparent.shape, dtype=bool) & transparent
    for c in range(3):
        std_val = max(bg_std[c], 1.0)
        z_dist = np.abs(source_rgb[:, :, c].astype(float) - bg_mean[c]) / std_val
        suspicious &= (z_dist > 3.0)
    
    print(f"    Found {suspicious.sum()} suspicious pixels", file=sys.stderr)
    
    if suspicious.sum() == 0:
        return [], bg_model
    
    print(f"    Labeling connected components...", file=sys.stderr)
    labeled, n_comps = label(suspicious)
    print(f"    Found {n_comps} components, filtering by area...", file=sys.stderr)
    
    # Use find_objects to get bounding boxes - much faster than iterating
    slices = find_objects(labeled)
    
    components = []
    for comp_id, (y_slice, x_slice) in enumerate(slices, start=1):
        if y_slice is None:
            continue
        
        # Check area first
        area = np.sum(labeled[y_slice, x_slice] == comp_id)
        if area < 200:
            continue
        
        y_min, y_max = y_slice.start, y_slice.stop
        x_min, x_max = x_slice.start, x_slice.stop
        
        # Compute mean z-score for this component
        mask = (labeled[y_slice, x_slice] == comp_id)
        y_coords, x_coords = np.where(mask)
        y_coords += y_min
        x_coords += x_min
        
        mean_z = 0.0
        for c in range(3):
            std_val = max(bg_std[c], 1.0)
            z_vals = np.abs(source_rgb[y_coords, x_coords, c].astype(float) - bg_mean[c]) / std_val
            mean_z += np.mean(z_vals ** 2)
        mean_z = np.sqrt(mean_z / 3.0)
        
        components.append((comp_id, (y_min, y_max, x_min, x_max), area, mean_z, labeled == comp_id))
    
    print(f"    Kept {len(components)} components with area >= 200", file=sys.stderr)
    components.sort(key=lambda x: x[2] * x[3], reverse=True)
    return components, bg_model

def detect_fringe_defects(result_rgba):
    """Detect white fringe at FG boundary using tile scanning."""
    print("  Computing FG mask and erosion...", file=sys.stderr)
    alpha = result_rgba[:, :, 3]
    rgb = result_rgba[:, :, :3]
    
    fg = (alpha > 0)
    
    print("  Eroding FG boundary...", file=sys.stderr)
    fg_interior = ndi.binary_erosion(fg, iterations=2)
    ring = fg & ~fg_interior
    
    if ring.sum() == 0:
        return []
    
    luma = (0.299 * rgb[:, :, 0].astype(float) +
            0.587 * rgb[:, :, 1].astype(float) +
            0.114 * rgb[:, :, 2].astype(float))
    
    print("  Scanning tiles for fringe...", file=sys.stderr)
    
    tile_h, tile_w = 256, 256
    tiles = []
    
    for y_idx in range(0, result_rgba.shape[0], tile_h):
        for x_idx in range(0, result_rgba.shape[1], tile_w):
            y_end = min(y_idx + tile_h, result_rgba.shape[0])
            x_end = min(x_idx + tile_w, result_rgba.shape[1])
            
            tile_ring = ring[y_idx:y_end, x_idx:x_end]
            tile_luma = luma[y_idx:y_end, x_idx:x_end]
            
            ring_count = np.sum(tile_ring)
            if ring_count < 10:
                continue
            
            high_luma = np.sum((tile_luma > 240) & tile_ring)
            fringe_score = high_luma / ring_count
            
            if fringe_score > 0.15:
                tiles.append((y_idx, x_idx, y_idx, x_idx, fringe_score))
    
    tiles.sort(key=lambda x: x[4], reverse=True)
    return tiles

def crop_pair_cutout(source_rgb, result_rgba, y_min, y_max, x_min, x_max, output_path):
    """Save 512px side-by-side crop: source | result on mid-grey."""
    h = y_max - y_min
    w = x_max - x_min
    pad = max(32, max(h, w) // 4)
    
    y_min_c = max(0, y_min - pad)
    y_max_c = min(result_rgba.shape[0], y_max + pad)
    x_min_c = max(0, x_min - pad)
    x_max_c = min(result_rgba.shape[1], x_max + pad)
    
    crop_h = y_max_c - y_min_c
    crop_w = x_max_c - x_min_c
    scale = min(1.0, 512.0 / max(crop_h, crop_w))
    
    new_h = int(crop_h * scale)
    new_w = int(crop_w * scale)
    
    src_crop = source_rgb[y_min_c:y_max_c, x_min_c:x_max_c]
    res_crop = result_rgba[y_min_c:y_max_c, x_min_c:x_max_c]
    
    if scale < 1.0:
        src_crop = np.array(Image.fromarray(src_crop).resize((new_w, new_h), Image.Resampling.LANCZOS))
        res_crop = np.array(Image.fromarray(res_crop).resize((new_w, new_h), Image.Resampling.LANCZOS))
    
    alpha = res_crop[:, :, 3:4] / 255.0
    res_on_grey = (res_crop[:, :, :3] * alpha + 127 * (1 - alpha)).astype(np.uint8)
    
    canvas = np.zeros((new_h, new_w * 2, 3), dtype=np.uint8)
    canvas[:, :new_w] = src_crop
    canvas[:, new_w:] = res_on_grey
    
    Image.fromarray(canvas).save(output_path)

def crop_pair_fringe(result_rgba, y_base, x_base, output_path):
    """Save 512px crop: result on mid-grey | result on black."""
    tile_h, tile_w = 256, 256
    y_end = min(y_base + tile_h, result_rgba.shape[0])
    x_end = min(x_base + tile_w, result_rgba.shape[1])
    
    crop = result_rgba[y_base:y_end, x_base:x_end]
    
    if crop.shape[0] < tile_h or crop.shape[1] < tile_w:
        crop = np.array(Image.fromarray(crop).resize((tile_w, tile_h), Image.Resampling.LANCZOS))
    
    alpha = crop[:, :, 3:4] / 255.0
    rgb = crop[:, :, :3]
    
    on_grey = (rgb * alpha + 127 * (1 - alpha)).astype(np.uint8)
    on_black = (rgb * alpha).astype(np.uint8)
    
    canvas = np.zeros((tile_h, tile_w * 2, 3), dtype=np.uint8)
    canvas[:, :tile_w] = on_grey
    canvas[:, tile_w:] = on_black
    
    Image.fromarray(canvas).save(output_path)

def main():
    parser = argparse.ArgumentParser(description="Scan bg-removed PNG for defects.")
    parser.add_argument("result_path", help="Path to RGBA result PNG")
    parser.add_argument("source_path", help="Path to RGB source PNG (white-bg)")
    parser.add_argument("--output-dir", default=None, help="Output dir for defect crops")
    args = parser.parse_args()
    
    result_path = Path(args.result_path)
    source_path = Path(args.source_path)
    
    if not result_path.exists():
        print(f"ERROR: result not found: {result_path}", file=sys.stderr)
        sys.exit(1)
    if not source_path.exists():
        print(f"ERROR: source not found: {source_path}", file=sys.stderr)
        sys.exit(1)
    
    output_dir = Path(args.output_dir) if args.output_dir else Path("/Users/za/Documents/product images repo/REVIEW/image14-bg/defects")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading result: {result_path}", file=sys.stderr)
    result_rgba = load_image(str(result_path), "RGBA")
    print(f"  Shape: {result_rgba.shape}", file=sys.stderr)
    
    print(f"Loading source: {source_path}", file=sys.stderr)
    source_rgb = load_image(str(source_path), "RGB")
    print(f"  Shape: {source_rgb.shape}", file=sys.stderr)
    
    print("\nScanning for cutout defects...", file=sys.stderr)
    cutout_comps, bg_model = detect_cutout_defects(result_rgba, source_rgb)
    print(f"  Total components with area >= 200: {len(cutout_comps)}", file=sys.stderr)
    
    cutout_crops_saved = 0
    for idx, (comp_id, (y_min, y_max, x_min, x_max), area, mean_z, mask) in enumerate(cutout_comps[:20]):
        out_path = output_dir / f"cutout-{idx:02d}-x{x_min}-y{y_min}.jpg"
        try:
            crop_pair_cutout(source_rgb, result_rgba, y_min, y_max, x_min, x_max, str(out_path))
            cutout_crops_saved += 1
            print(f"  [{idx+1}/20] {out_path.name}", file=sys.stderr)
        except Exception as e:
            print(f"  [{idx+1}/20] ERROR: {e}", file=sys.stderr)
    
    print("\nScanning for fringe defects...", file=sys.stderr)
    fringe_tiles = detect_fringe_defects(result_rgba)
    print(f"  Total tiles with score > 0.15: {len(fringe_tiles)}", file=sys.stderr)
    
    fringe_crops_saved = 0
    for idx, (y_idx, x_idx, y_base, x_base, fringe_score) in enumerate(fringe_tiles[:20]):
        out_path = output_dir / f"fringe-{idx:02d}-x{x_base}-y{y_base}.jpg"
        try:
            crop_pair_fringe(result_rgba, y_base, x_base, str(out_path))
            fringe_crops_saved += 1
            print(f"  [{idx+1}/20] {out_path.name}", file=sys.stderr)
        except Exception as e:
            print(f"  [{idx+1}/20] ERROR: {e}", file=sys.stderr)
    
    total_cutout_px = sum(comp[2] for comp in cutout_comps)
    bg_mean, bg_std = bg_model
    bg_mean_str = f"({int(bg_mean[0])}, {int(bg_mean[1])}, {int(bg_mean[2])})"
    bg_std_str = f"({bg_std[0]:.1f}, {bg_std[1]:.1f}, {bg_std[2]:.1f})"
    
    print("\n" + "="*70)
    print("DEFECT SCAN SUMMARY")
    print("="*70)
    print(f"Result: {result_path.name}")
    print(f"Source: {source_path.name}")
    print(f"Output: {output_dir}")
    print()
    
    print(f"CUTOUT DEFECTS (transparent px far from BG model):")
    print(f"  Total components: {len(cutout_comps)}")
    print(f"  Total suspicious pixels: {total_cutout_px}")
    print(f"  BG model (mean RGB): {bg_mean_str}")
    print(f"  BG model (std RGB): {bg_std_str}")
    print(f"  Crops saved: {cutout_crops_saved}/20")
    print()
    
    print(f"FRINGE DEFECTS (high-luma FG boundary):")
    print(f"  Total tiles with score > 0.15: {len(fringe_tiles)}")
    print(f"  Crops saved: {fringe_crops_saved}/20")
    print()
    
    if len(cutout_comps) > 0:
        print("TOP 10 CUTOUT DEFECTS (by area * mean_z):")
        print(f"  {'#':<3} {'Coords (x,y)':<25} {'Area':<8} {'Z-Score':<8}")
        print("  " + "-"*55)
        for idx, (_, (y_min, y_max, x_min, x_max), area, mean_z, _) in enumerate(cutout_comps[:10]):
            print(f"  {idx+1:<3} ({x_min:4d},{y_min:4d})-({x_max:4d},{y_max:4d})  {area:<8} {mean_z:<8.2f}")
        print()
    else:
        print("TOP 10 CUTOUT DEFECTS: none detected")
        print()
    
    if len(fringe_tiles) > 0:
        print("TOP 10 FRINGE DEFECTS (by fringe_score):")
        print(f"  {'#':<3} {'Tile (x,y)':<25} {'Score':<8}")
        print("  " + "-"*40)
        for idx, (y_idx, x_idx, _, _, fringe_score) in enumerate(fringe_tiles[:10]):
            print(f"  {idx+1:<3} ({x_idx:5d},{y_idx:5d})           {fringe_score:.3f}")
        print()
    else:
        print("TOP 10 FRINGE DEFECTS: none detected")
        print()
    
    print("OUTPUT DIRECTORY LISTING:")
    print(f"  {output_dir}/")
    if output_dir.exists():
        files = sorted(output_dir.glob("*.jpg"))
        if files:
            for f in files:
                size_mb = f.stat().st_size / (1024*1024)
                print(f"    {f.name:<60} {size_mb:>6.1f} MB")
        else:
            print(f"    (no crops saved)")
    print()
    
    print("="*70)
    print("Facts only. Review crops in the output directory.")

if __name__ == "__main__":
    main()
