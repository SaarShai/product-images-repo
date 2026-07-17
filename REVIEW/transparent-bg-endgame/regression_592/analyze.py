#!/usr/bin/env python3
"""R38 visual re-validation: diff current-HEAD purge output vs banked round-7
purged.png, cluster changed pixels, render 12x NEAREST side-by-side boards
(banked | new | diff-heatmap) for the top clusters.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

SCRATCH = Path("/private/tmp/claude-501/-Users-za-Documents-product-images-repo/9e28116f-996a-4c1c-b186-03b4fd007754/scratchpad/regression_592")
BANKED_DIR = Path("/Users/za/Documents/product images repo/tasks/transparent-bg-endgame/round7_outline/processed")
OUT_ROOT = Path("/Users/za/Documents/product images repo/REVIEW/transparent-bg-endgame/regression_592")

ZOOM = 12
CTX = 24  # context px around cluster bbox (pre-zoom pixels)
DILATE_ITERS = 1  # merge near-neighbor changed px into one cluster
TOP_N = 12

def load_rgba(path):
    return np.array(Image.open(path).convert("RGBA"))

def font(size=16):
    for candidate in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                pass
    return ImageFont.load_default()

def analyze(tag):
    new_path = SCRATCH / f"purged-{tag}.png"
    banked_path = BANKED_DIR / f"H-G2-OUT-GREEN-{tag}-purged.png"
    new = load_rgba(new_path).astype(np.int16)
    banked = load_rgba(banked_path).astype(np.int16)
    assert new.shape == banked.shape, (new.shape, banked.shape)

    diff_any = np.any(new != banked, axis=2)  # bool HxW
    alpha_diff = new[:, :, 3] != banked[:, :, 3]
    rgb_delta = np.abs(new[:, :, :3] - banked[:, :, :3])  # HxWx3
    per_px_max_delta = rgb_delta.max(axis=2)
    per_px_mean_delta = rgb_delta.mean(axis=2)

    n_changed = int(diff_any.sum())
    n_alpha_changed = int(alpha_diff.sum())

    # connected-component clustering with small dilation to merge near neighbors
    struct = ndimage.generate_binary_structure(2, 2)  # 8-connectivity
    dilated = ndimage.binary_dilation(diff_any, structure=struct, iterations=DILATE_ITERS)
    labeled, n_labels = ndimage.label(dilated, structure=struct)
    # restrict labels back to actual changed pixels only (dilation was just for merging)
    labeled_at_changed = labeled * diff_any

    clusters = []
    for lbl in range(1, n_labels + 1):
        mask = labeled_at_changed == lbl
        px = int(mask.sum())
        if px == 0:
            continue
        ys, xs = np.where(mask)
        y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
        max_d = int(per_px_max_delta[mask].max())
        mean_d = float(per_px_mean_delta[mask].mean())
        clusters.append({
            "label": int(lbl),
            "px": px,
            "bbox": (int(y0), int(y1), int(x0), int(x1)),
            "max_delta": max_d,
            "mean_delta": round(mean_d, 2),
        })
    clusters.sort(key=lambda c: -c["px"])

    stats = {
        "tag": tag,
        "changed_px": n_changed,
        "alpha_changed_px": n_alpha_changed,
        "n_clusters": len(clusters),
        "mean_delta_over_changed_px": round(float(per_px_mean_delta[diff_any].mean()), 2) if n_changed else 0.0,
        "max_delta_over_changed_px": int(per_px_max_delta[diff_any].max()) if n_changed else 0,
    }
    return new.astype(np.uint8), banked.astype(np.uint8), clusters, stats


def make_heatmap(rgb_delta_crop, alpha_mask=None):
    """rgb_delta_crop: HxWx3 abs delta 0-255ish. Map max-channel-delta to a
    red-hot heatmap on black."""
    mag = rgb_delta_crop.max(axis=2).astype(np.float32)
    mx = mag.max() if mag.max() > 0 else 1.0
    norm = np.clip(mag / mx, 0, 1)
    heat = np.zeros((*mag.shape, 3), dtype=np.uint8)
    heat[:, :, 0] = (norm * 255).astype(np.uint8)  # R
    heat[:, :, 1] = (norm * 80).astype(np.uint8)   # slight G for orange-hot look
    return Image.fromarray(heat, "RGB")


def draw_label(img, text, pad=4):
    """Return a new image with a label bar drawn above img."""
    fnt = font(15)
    bar_h = 20
    w = img.width
    out = Image.new("RGB", (w, img.height + bar_h), (20, 20, 20))
    out.paste(img.convert("RGB"), (0, bar_h))
    d = ImageDraw.Draw(out)
    d.text((pad, 2), text, fill=(255, 255, 255), font=fnt)
    return out


def checker_bg(w, h, cell=6):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            if ((x // cell) + (y // cell)) % 2 == 0:
                arr[y:y + cell, x:x + cell] = (200, 200, 200)
            else:
                arr[y:y + cell, x:x + cell] = (150, 150, 150)
    return arr


def composite_on_checker(rgba_crop):
    h, w = rgba_crop.shape[:2]
    bg = checker_bg(w, h)
    a = rgba_crop[:, :, 3:4].astype(np.float32) / 255.0
    rgb = rgba_crop[:, :, :3].astype(np.float32)
    out = (rgb * a + bg.astype(np.float32) * (1 - a)).astype(np.uint8)
    return out


def render_cluster_board(new, banked, cluster, tag, idx, boards_dir):
    y0, y1, x0, x1 = cluster["bbox"]
    H, W = new.shape[:2]
    cy0 = max(0, y0 - CTX)
    cy1 = min(H, y1 + CTX + 1)
    cx0 = max(0, x0 - CTX)
    cx1 = min(W, x1 + CTX + 1)

    banked_crop = banked[cy0:cy1, cx0:cx1]
    new_crop = new[cy0:cy1, cx0:cx1]
    rgb_delta_crop = np.abs(new_crop[:, :, :3].astype(np.int16) - banked_crop[:, :, :3].astype(np.int16))

    banked_comp = composite_on_checker(banked_crop)
    new_comp = composite_on_checker(new_crop)
    heat_img = make_heatmap(rgb_delta_crop)

    ch, cw = banked_comp.shape[:2]
    zh, zw = ch * ZOOM, cw * ZOOM

    banked_img = Image.fromarray(banked_comp, "RGB").resize((zw, zh), Image.NEAREST)
    new_img = Image.fromarray(new_comp, "RGB").resize((zw, zh), Image.NEAREST)
    heat_img_z = heat_img.resize((zw, zh), Image.NEAREST)

    banked_lbl = draw_label(banked_img, "BANKED (round-7 purged)")
    new_lbl = draw_label(new_img, "NEW (current-HEAD purge)")
    heat_lbl = draw_label(heat_img_z, "DIFF HEATMAP (max-channel |delta|)")

    gap = 12
    total_w = banked_lbl.width + gap + new_lbl.width + gap + heat_lbl.width
    total_h = max(banked_lbl.height, new_lbl.height, heat_lbl.height) + 34
    board = Image.new("RGB", (total_w, total_h), (10, 10, 10))
    x = 0
    board.paste(banked_lbl, (x, 34)); x += banked_lbl.width + gap
    board.paste(new_lbl, (x, 34)); x += new_lbl.width + gap
    board.paste(heat_lbl, (x, 34))

    d = ImageDraw.Draw(board)
    title_fnt = font(18)
    title = (f"{tag} cluster #{idx+1}  |  px={cluster['px']}  "
             f"bbox=({x0},{y0})-({x1},{y1})  "
             f"maxΔ={cluster['max_delta']}  meanΔ={cluster['mean_delta']}")
    d.text((6, 6), title, fill=(255, 255, 0), font=title_fnt)

    out_path = boards_dir / f"{tag}-cluster{idx+1:02d}_px{cluster['px']}.png"
    board.save(out_path)
    return out_path


def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    boards_dir = OUT_ROOT / "boards"
    boards_dir.mkdir(exist_ok=True)
    fullres_dir = OUT_ROOT / "fullres"
    fullres_dir.mkdir(exist_ok=True)

    all_stats = {}
    all_cluster_tables = {}
    board_paths = {}

    for tag in ["r1", "r2"]:
        new, banked, clusters, stats = analyze(tag)
        all_stats[tag] = stats
        all_cluster_tables[tag] = clusters

        # copy fullres purged outputs (both banked + new) into fullres/
        Image.fromarray(banked, "RGBA").save(fullres_dir / f"H-G2-OUT-GREEN-{tag}-purged-BANKED.png")
        Image.fromarray(new, "RGBA").save(fullres_dir / f"H-G2-OUT-GREEN-{tag}-purged-NEW.png")

        top_clusters = clusters[:TOP_N]
        paths = []
        for idx, c in enumerate(top_clusters):
            p = render_cluster_board(new, banked, c, tag, idx, boards_dir)
            paths.append(str(p))
        board_paths[tag] = paths

        with open(OUT_ROOT / f"{tag}-clusters.json", "w") as f:
            json.dump({"stats": stats, "clusters": clusters}, f, indent=2)

    with open(OUT_ROOT / "all_stats.json", "w") as f:
        json.dump(all_stats, f, indent=2)

    print(json.dumps(all_stats, indent=2))
    for tag, paths in board_paths.items():
        print(tag, "boards:", len(paths))


if __name__ == "__main__":
    main()
