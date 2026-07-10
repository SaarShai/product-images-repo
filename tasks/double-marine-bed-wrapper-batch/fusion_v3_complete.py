#!/usr/bin/env python3
"""Complete watercolor bg-removal: open enclosed paper, restore pale paint, kill fringe.

Solves the three residual failure modes left by fusion v1 / property-cleanup:
  1. white fringe at edges
  2. pale paint wrongly deleted
  3. enclosed paper holes left opaque

Architecture (flood-first, NOT BRIA-first):
  - PAPER = corner-calibrated near-white NEUTRAL only (chroma<=5)
  - flood_bg = border-connected PAPER → transparent
  - FG starts as ~flood_bg (keeps ghost-layer pale paint BRIA drops)
  - punch enclosed PAPER (true holes between branches)
  - optional: punch BRIA-transparent near-paper pockets still opaque
  - restore non-paper transparent components that touch FG
  - forced 1px erode + white un-matte + decontam + luma cap
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

Image.MAX_IMAGE_PIXELS = None

REPO = Path(__file__).resolve().parents[2]
PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)


@dataclass
class Params:
    paper_chroma_max: float = 5.0
    paper_luma_min: float = 248.0
    paper_dist_max: float = 8.0
    restore_min_chroma: float = 4.0
    restore_max_luma: float = 248.0
    restore_min_dist: float = 3.5
    restore_min_area: int = 16
    restore_max_area: int = 200_000
    hole_min_area: int = 32
    adaptive_erode_cap: int = 4
    adaptive_erode_luma: float = 245.0
    defringe_width: int = 6
    luma_cap: float = 235.0
    small_fg_min_area: int = 12
    forced_erode: int = 1


def luma_chroma(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rgb16 = rgb.astype(np.uint16)
    luma = ((77 * rgb16[:, :, 0] + 150 * rgb16[:, :, 1] + 29 * rgb16[:, :, 2]) >> 8).astype(
        np.float32
    )
    mx = np.maximum(np.maximum(rgb[:, :, 0], rgb[:, :, 1]), rgb[:, :, 2]).astype(np.float32)
    mn = np.minimum(np.minimum(rgb[:, :, 0], rgb[:, :, 1]), rgb[:, :, 2]).astype(np.float32)
    return luma, (mx - mn)


def paper_model(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = rgb.shape[:2]
    py, px = max(12, h // 50), max(12, w // 50)
    samples = np.concatenate(
        [
            rgb[:py, :px].reshape(-1, 3),
            rgb[:py, -px:].reshape(-1, 3),
            rgb[-py:, :px].reshape(-1, 3),
            rgb[-py:, -px:].reshape(-1, 3),
        ],
        axis=0,
    ).astype(np.float32)
    mean = samples.mean(axis=0)
    std = np.maximum(samples.std(axis=0), 1.0)
    return mean, std


def bg_distance(rgb: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    z = (rgb.astype(np.float32) - mean[None, None, :]) / std[None, None, :]
    return np.sqrt((z * z).sum(axis=2))


def border_connected(mask: np.ndarray) -> np.ndarray:
    labels, count = ndi.label(mask)
    if count == 0:
        return np.zeros_like(mask, dtype=bool)
    border_ids = set(labels[0, :].tolist())
    border_ids.update(labels[-1, :].tolist())
    border_ids.update(labels[:, 0].tolist())
    border_ids.update(labels[:, -1].tolist())
    border_ids.discard(0)
    if not border_ids:
        return np.zeros_like(mask, dtype=bool)
    return np.isin(labels, list(border_ids))


def remove_small(mask: np.ndarray, min_area: int) -> tuple[np.ndarray, int]:
    labels, count = ndi.label(mask)
    if count == 0:
        return mask, 0
    areas = np.bincount(labels.ravel())
    keep = areas >= min_area
    keep[0] = False
    out = keep[labels]
    return out, int((mask & ~out).sum())


def restore_paint_components(
    fg: np.ndarray,
    candidates: np.ndarray,
    luma: np.ndarray,
    chroma: np.ndarray,
    dist: np.ndarray,
    p: Params,
) -> tuple[np.ndarray, dict[str, Any]]:
    labels, count = ndi.label(candidates)
    restored = np.zeros_like(fg, dtype=bool)
    n_restored = 0
    px_restored = 0
    dilated = ndi.binary_dilation(fg, iterations=1)
    objects = ndi.find_objects(labels) if count else []
    for cid, slc in enumerate(objects, start=1):
        if slc is None:
            continue
        ys, xs = slc
        comp = labels[ys, xs] == cid
        area = int(comp.sum())
        if area < p.restore_min_area or area > p.restore_max_area:
            continue
        y0, y1 = max(0, ys.start - 1), min(fg.shape[0], ys.stop + 1)
        x0, x1 = max(0, xs.start - 1), min(fg.shape[1], xs.stop + 1)
        comp_pad = labels[y0:y1, x0:x1] == cid
        if not bool((comp_pad & dilated[y0:y1, x0:x1]).any()):
            continue
        med_luma = float(np.median(luma[ys, xs][comp]))
        med_chroma = float(np.median(chroma[ys, xs][comp]))
        mean_dist = float(dist[ys, xs][comp].mean())
        paint_like = (
            med_chroma >= p.restore_min_chroma
            or med_luma <= p.restore_max_luma
            or mean_dist >= p.restore_min_dist
        )
        if not paint_like:
            continue
        restored[ys, xs] |= comp
        n_restored += 1
        px_restored += area
    return fg | restored, {
        "restore_components": n_restored,
        "restore_px": px_restored,
        "candidate_components": int(count),
    }


def punch_enclosed_paper(
    fg: np.ndarray, enclosed_paper: np.ndarray, min_area: int
) -> tuple[np.ndarray, dict[str, Any]]:
    labels, count = ndi.label(enclosed_paper & fg)
    punched = np.zeros_like(fg, dtype=bool)
    n = 0
    px = 0
    objects = ndi.find_objects(labels) if count else []
    for cid, slc in enumerate(objects, start=1):
        if slc is None:
            continue
        ys, xs = slc
        comp = labels[ys, xs] == cid
        area = int(comp.sum())
        if area < min_area:
            continue
        punched[ys, xs] |= comp
        n += 1
        px += area
    return fg & ~punched, {"hole_components_opened": n, "hole_px_opened": px}


def adaptive_erode(fg: np.ndarray, luma: np.ndarray, p: Params) -> tuple[np.ndarray, int]:
    out = fg.copy()
    eroded_iters = 0
    for i in range(1, p.adaptive_erode_cap + 1):
        eroded = ndi.binary_erosion(out, iterations=1)
        ring = out & ~eroded
        if not ring.any():
            break
        med = float(np.median(luma[ring]))
        if med < p.adaptive_erode_luma:
            break
        out = eroded
        eroded_iters = i
    return out, eroded_iters


def decontaminate_boundary(
    rgb: np.ndarray, mask: np.ndarray, width: int = 6
) -> tuple[np.ndarray, int]:
    sat_num = rgb.max(2).astype(np.float32) - rgb.min(2).astype(np.float32)
    val = rgb.max(2).astype(np.float32) / 255.0
    sat = np.zeros_like(val)
    mx = rgb.max(2).astype(np.float32)
    nz = mx > 0
    sat[nz] = sat_num[nz] / mx[nz]
    dist_in = ndi.distance_transform_edt(mask)
    boundary = mask & (dist_in <= width)
    whiteish = (val >= 0.88) & (sat <= 0.22) & (sat_num <= 55)
    replace = boundary & whiteish
    if not replace.any():
        return rgb.copy(), 0
    safe = mask & (dist_in >= width + 2) & ((val < 0.84) | (sat > 0.14) | (sat_num > 28))
    if int(safe.sum()) < 64:
        safe = mask & (dist_in >= width + 2)
    if int(safe.sum()) < 64:
        return rgb.copy(), 0
    _, nearest = ndi.distance_transform_edt(~safe, return_indices=True)
    yy, xx = nearest
    out = rgb.copy()
    out[replace] = rgb[yy[replace], xx[replace]]
    return out, int(replace.sum())


def luma_cap_boundary(
    rgb: np.ndarray, mask: np.ndarray, width: int, target: float
) -> tuple[np.ndarray, int]:
    luma, _ = luma_chroma(rgb)
    dist_in = ndi.distance_transform_edt(mask)
    boundary = mask & (dist_in <= width) & (luma > target)
    if not boundary.any():
        return rgb, 0
    out = rgb.copy()
    scale = target / np.maximum(luma[boundary], 1.0)
    out[boundary] = np.clip(out[boundary].astype(np.float32) * scale[:, None], 0, 255).astype(
        np.uint8
    )
    return out, int(boundary.sum())


def unmatte_white_boundary(
    rgb: np.ndarray,
    mask: np.ndarray,
    paper_mean: np.ndarray,
    width: int = 4,
) -> tuple[np.ndarray, int]:
    """Remove white-matte contamination in a hard-alpha boundary band."""
    dist_in = ndi.distance_transform_edt(mask)
    boundary = mask & (dist_in <= width)
    if not boundary.any():
        return rgb.copy(), 0
    safe = mask & (dist_in >= width + 2)
    if int(safe.sum()) < 64:
        safe = mask & (dist_in >= width + 1)
    if int(safe.sum()) < 64:
        return rgb.copy(), 0
    _, nearest = ndi.distance_transform_edt(~safe, return_indices=True)
    yy, xx = nearest
    interior = rgb[yy, xx].astype(np.float32)
    paper = paper_mean.astype(np.float32)
    cur = rgb.astype(np.float32)
    diff_c = cur - paper[None, None, :]
    diff_f = interior - paper[None, None, :]
    num = np.sqrt((diff_c * diff_c).sum(axis=2))
    den = np.sqrt((diff_f * diff_f).sum(axis=2))
    a = np.clip(num / np.maximum(den, 1e-3), 0.15, 1.0)
    closer_to_paper = num < (0.95 * den)
    replace = boundary & closer_to_paper
    if not replace.any():
        return rgb.copy(), 0
    out = rgb.copy()
    aa = a[replace][:, None]
    unblended = (cur[replace] - (1.0 - aa) * paper[None, :]) / aa
    use_interior = (unblended.max(axis=1) > 252) | (unblended.min(axis=1) < 0)
    fixed = np.where(use_interior[:, None], interior[replace], np.clip(unblended, 0, 255))
    out[replace] = fixed.astype(np.uint8)
    return out, int(replace.sum())


def run_pipeline(
    rgb: np.ndarray,
    bria_fg: np.ndarray,
    p: Params,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Flood-first FG + enclosed-paper punch + forced erode + white un-matte."""
    assert rgb.shape[:2] == bria_fg.shape
    mean, std = paper_model(rgb)
    luma, chroma = luma_chroma(rgb)
    dist = bg_distance(rgb, mean, std)

    paper = (luma >= p.paper_luma_min) & (chroma <= p.paper_chroma_max) & (dist <= p.paper_dist_max)
    flood_bg = border_connected(paper)
    enclosed_paper = paper & ~flood_bg

    fg = ~flood_bg
    fg, hole_stats = punch_enclosed_paper(fg, enclosed_paper, p.hole_min_area)

    bria_holes = (~bria_fg) & fg
    near_paper = (luma >= p.paper_luma_min - 3) & (chroma <= p.paper_chroma_max + 3) & (
        dist <= p.paper_dist_max + 2
    )
    near_paper_enclosed = near_paper & ~border_connected(near_paper)
    extra_hole_cand = bria_holes & near_paper_enclosed
    fg, extra_hole_stats = punch_enclosed_paper(
        fg, extra_hole_cand, max(8, p.hole_min_area // 2)
    )

    candidates = (~fg) & (~paper)
    fg, restore_stats = restore_paint_components(fg, candidates, luma, chroma, dist, p)

    fg, removed_small = remove_small(fg, p.small_fg_min_area)

    if p.forced_erode > 0:
        fg = ndi.binary_erosion(fg, iterations=p.forced_erode)
    fg, erode_extra = adaptive_erode(fg, luma, p)
    erode_iters = p.forced_erode + erode_extra

    rgb_out = rgb.copy()
    rgb_out, unmatte_n = unmatte_white_boundary(
        rgb_out, fg, mean, width=max(3, p.defringe_width - 2)
    )
    rgb_out, decontam_n = decontaminate_boundary(rgb_out, fg, width=p.defringe_width)
    rgb_out, cap_n = luma_cap_boundary(rgb_out, fg, width=p.defringe_width, target=p.luma_cap)

    metrics = {
        "paper_mean_rgb": [float(x) for x in mean],
        "paper_std_rgb": [float(x) for x in std],
        "paper_px": int(paper.sum()),
        "flood_bg_px": int(flood_bg.sum()),
        "enclosed_paper_px": int(enclosed_paper.sum()),
        "bria_fg_px": int(bria_fg.sum()),
        "final_fg_px": int(fg.sum()),
        "removed_small_fg_px": removed_small,
        "adaptive_erode_iters": erode_iters,
        "unmatte_px": unmatte_n,
        "decontam_px": decontam_n,
        "luma_cap_px": cap_n,
        "extra_bria_hole_px": extra_hole_stats.get("hole_px_opened", 0),
        **hole_stats,
        **restore_stats,
        "params": asdict(p),
    }
    return fg, rgb_out, metrics


def alpha_hist(mask: np.ndarray) -> dict[str, float]:
    n = mask.size
    op = int(mask.sum())
    return {
        "opaque_pct": 100.0 * op / n,
        "transparent_pct": 100.0 * (n - op) / n,
        "semi_pct": 0.0,
    }


def score_rois(
    fg: np.ndarray,
    src_rgb: np.ndarray,
    rois: list[tuple[str, int, int, int, int]],
) -> dict[str, Any]:
    luma, chroma = luma_chroma(src_rgb)
    out: dict[str, Any] = {}
    for name, x, y, w, h in rois:
        a = fg[y : y + h, x : x + w]
        lu = luma[y : y + h, x : x + w]
        ch = chroma[y : y + h, x : x + w]
        trans = ~a
        opaq = a
        wrong = int((trans & ((ch > 8) | (lu < 245))).sum())
        paperish = int((opaq & (lu >= 248) & (ch <= 6)).sum())
        ring = opaq & ~ndi.binary_erosion(opaq, iterations=2)
        fringe = float(((ring) & (lu >= 240)).sum() / max(int(ring.sum()), 1))
        out[name] = {
            "wrong_cut_px": wrong,
            "opaque_paperish_px": paperish,
            "fringe_score": fringe,
            "trans_pct": float(100.0 * trans.mean()),
        }
    return out


def load_image14_x4() -> tuple[np.ndarray, np.ndarray, Path]:
    x4_rgb = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-rgb/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-rgb.png"
    )
    bria = PRODUCT / (
        "Images/candidates/image14-research/candidates/"
        "14-01-bria-rmbg-alpha-matting-hard180.png"
    )
    hard180_x4 = PRODUCT / (
        "Images/candidates/batch-x8-hard180/x4-hard180/"
        "14-ChatGPT_Image_Jul_7_2026_11_22_35_AM@x4-hard180-colorrestore.png"
    )
    rgb = np.asarray(Image.open(x4_rgb).convert("RGB"), dtype=np.uint8)
    if hard180_x4.exists():
        alpha_img = Image.open(hard180_x4).convert("RGBA")
        if alpha_img.size != (rgb.shape[1], rgb.shape[0]):
            alpha_img = alpha_img.resize((rgb.shape[1], rgb.shape[0]), Image.Resampling.NEAREST)
        fg = np.asarray(alpha_img)[:, :, 3] >= 128
        src = hard180_x4
    else:
        alpha_img = Image.open(bria).convert("RGBA")
        if alpha_img.size != (rgb.shape[1], rgb.shape[0]):
            alpha_img = alpha_img.resize((rgb.shape[1], rgb.shape[0]), Image.Resampling.NEAREST)
        fg = np.asarray(alpha_img)[:, :, 3] >= 128
        src = bria
    return rgb, fg, src


def save_rgba(path: Path, rgb: np.ndarray, fg: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rgba = np.empty((*fg.shape, 4), dtype=np.uint8)
    rgba[:, :, :3] = rgb
    rgba[:, :, 3] = np.where(fg, 255, 0).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(path, optimize=True)


def make_review_crop(
    out_path: Path,
    rgb: np.ndarray,
    fg: np.ndarray,
    x: int,
    y: int,
    w: int,
    h: int,
    scale: int = 2,
) -> None:
    patch_rgb = rgb[y : y + h, x : x + w]
    patch_fg = fg[y : y + h, x : x + w]
    gray = np.full_like(patch_rgb, 140)
    black = np.zeros_like(patch_rgb)
    mag = np.zeros_like(patch_rgb)
    mag[:, :, 0] = 255
    mag[:, :, 2] = 255
    on_gray = np.where(patch_fg[:, :, None], patch_rgb, gray)
    on_black = np.where(patch_fg[:, :, None], patch_rgb, black)
    on_mag = np.where(patch_fg[:, :, None], patch_rgb, mag)
    board = np.concatenate([patch_rgb, on_gray, on_black, on_mag], axis=1)
    im = Image.fromarray(board, "RGB")
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, quality=92)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", choices=("x4", "x8"), default="x4")
    ap.add_argument("--out-dir", type=Path, default=None)
    args = ap.parse_args()

    p = Params()
    if args.scale == "x4":
        rgb, bria_fg, bria_path = load_image14_x4()
        x8_w, x8_h = 7528, 13376
        sx = rgb.shape[1] / x8_w
        sy = rgb.shape[0] / x8_h

        def sx8(x: int, y: int, w: int, h: int) -> tuple[int, int, int, int]:
            return int(x * sx), int(y * sy), max(1, int(w * sx)), max(1, int(h * sy))

        rois = [
            ("cut00", *sx8(3601, 6253, 320, 400)),
            ("cut01", *sx8(2175, 7911, 232, 200)),
            ("cut02", *sx8(4447, 7013, 181, 200)),
            ("enclosed_tri", *sx8(6452 - 128, 5548 - 128, 256, 256)),
            ("fringe_purple", *sx8(533 - 128, 7908 - 128, 256, 256)),
            ("fringe_pink", *sx8(4355 - 128, 5013 - 128, 256, 256)),
        ]
    else:
        raise SystemExit("x8 path not wired in this thin proof; run x4 first")

    out_dir = args.out_dir or (REPO / "Images/candidates/image14-research/fusion-v3-complete")
    out_dir.mkdir(parents=True, exist_ok=True)
    review = REPO / "REVIEW/image14-bg/fusion-v3-complete"
    review.mkdir(parents=True, exist_ok=True)

    fg, rgb_out, metrics = run_pipeline(rgb, bria_fg, p)
    hist = alpha_hist(fg)
    roi_scores = score_rois(fg, rgb, rois)
    metrics["alpha"] = hist
    metrics["roi_scores"] = roi_scores
    metrics["bria_source"] = str(bria_path)
    metrics["rgb_shape"] = list(rgb.shape)

    out_png = out_dir / "14-fusion-v3-complete-x4.png"
    save_rgba(out_png, rgb_out, fg)
    (out_dir / "14-fusion-v3-complete-x4-metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    for name, x, y, w, h in rois:
        make_review_crop(review / f"{name}.jpg", rgb_out, fg, x, y, w, h, scale=2)

    gray = np.full_like(rgb_out, 140)
    comp = np.where(fg[:, :, None], rgb_out, gray)
    prev = Image.fromarray(comp, "RGB")
    prev.thumbnail((1200, 2000), Image.Resampling.LANCZOS)
    prev.save(review / "full-gray-preview.jpg", quality=90)

    print(
        json.dumps(
            {
                "out_png": str(out_png),
                "alpha": hist,
                "roi_scores": roi_scores,
                "summary": {
                    "restore_px": metrics["restore_px"],
                    "hole_px_opened": metrics["hole_px_opened"],
                    "extra_bria_hole_px": metrics["extra_bria_hole_px"],
                    "adaptive_erode_iters": metrics["adaptive_erode_iters"],
                    "unmatte_px": metrics["unmatte_px"],
                    "decontam_px": metrics["decontam_px"],
                    "luma_cap_px": metrics["luma_cap_px"],
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
