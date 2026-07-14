#!/usr/bin/env python3
"""review_pack.py — build a review pack for a Route C-green v2 (or any RGBA)
candidate: fullres copy, dark/white/magenta composites, gate D5 crops (if the
gate battery emitted them), and deterministic junction/concavity crops at
4x LANCZOS and 12x NEAREST.

Standalone:
    /usr/bin/python3 scripts/review_pack.py \\
      --final FINAL.png --raw RAW.png --out-dir PACK_DIR \\
      [--gate-dir GATES_DIR] [--n-crops 6] [--crop-size 96]

Also importable — `build_review_pack(...)` is called directly by
scripts/run_c_green_v2.py.

Nothing is silently omitted: every crop and composite written is listed in
PACK_DIR/manifest.json.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

COMPOSITE_BACKGROUNDS = {
    "dark": (17, 17, 17),      # #111
    "white": (255, 255, 255),
    "magenta": (255, 0, 255),
}


def composite_rgb(rgba: np.ndarray, bg: tuple[int, int, int]) -> np.ndarray:
    rgb = rgba[..., :3].astype(np.float32)
    alpha = rgba[..., 3:4].astype(np.float32) / 255.0
    bg_arr = np.array(bg, dtype=np.float32)
    return np.clip(np.round(rgb * alpha + bg_arr * (1.0 - alpha)), 0, 255).astype(np.uint8)


def _alpha_boundary_curvature_points(alpha: np.ndarray, n: int) -> list[tuple[int, int]]:
    """Deterministically pick up to `n` high-curvature / high-boundary-density
    points on the alpha silhouette boundary (junctions, concave notches are
    exactly where curvature/boundary-density spikes).

    Method: binarize alpha, take the boundary (dilate XOR erode), then for
    each boundary pixel score = local boundary-pixel density in a small
    window (high density ~= junction/notch, not a smooth straight edge).
    Pick the top-N local maxima, spaced apart by non-max suppression, ordered
    by (score desc, y, x) for determinism.
    """
    fg = alpha > 127
    if not fg.any():
        return []
    struct = np.ones((3, 3), dtype=bool)
    dil = ndi.binary_dilation(fg, structure=struct, iterations=2)
    ero = ndi.binary_erosion(fg, structure=struct, iterations=2)
    boundary = dil & ~ero
    if not boundary.any():
        return []

    # local density = boundary-pixel count in a 15x15 window (curvature proxy)
    density = ndi.uniform_filter(boundary.astype(np.float32), size=15)
    density[~boundary] = -1.0

    ys, xs = np.nonzero(boundary)
    scores = density[ys, xs]
    order = np.lexsort((xs, ys, -scores))  # score desc primary, then y, x for ties

    picked: list[tuple[int, int]] = []
    min_sep = 40
    for idx in order:
        y, x = int(ys[idx]), int(xs[idx])
        if all((y - py) ** 2 + (x - px) ** 2 >= min_sep ** 2 for py, px in picked):
            picked.append((y, x))
        if len(picked) >= n:
            break
    return picked


def _crop_at(img: Image.Image, cx: int, cy: int, half: int) -> Image.Image:
    w, h = img.size
    left = max(0, min(w - 2 * half, cx - half))
    top = max(0, min(h - 2 * half, cy - half))
    left = max(0, left)
    top = max(0, top)
    right = min(w, left + 2 * half)
    bottom = min(h, top + 2 * half)
    return img.crop((left, top, right, bottom))


def build_review_pack(
    final_path: Path,
    raw_path: Path | None,
    out_dir: Path,
    gate_dir: Path | None = None,
    n_crops: int = 6,
    crop_size: int = 96,
) -> dict[str, Any]:
    """Build the review pack. Returns the manifest dict (also written to
    out_dir/manifest.json)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "final_source": str(final_path),
        "raw_source": str(raw_path) if raw_path else None,
        "gate_dir_source": str(gate_dir) if gate_dir else None,
        "files": [],
    }

    def _record(kind: str, path: Path, extra: dict[str, Any] | None = None) -> None:
        entry = {"kind": kind, "path": str(path)}
        if extra:
            entry.update(extra)
        manifest["files"].append(entry)

    # 1. fullres copy
    fullres_dir = out_dir / "fullres"
    fullres_dir.mkdir(parents=True, exist_ok=True)
    final_copy = fullres_dir / f"final{final_path.suffix}"
    shutil.copy2(final_path, final_copy)
    _record("fullres_final", final_copy)

    if raw_path is not None and raw_path.exists():
        raw_copy = fullres_dir / f"raw{raw_path.suffix}"
        shutil.copy2(raw_path, raw_copy)
        _record("fullres_raw", raw_copy)

    final_img = Image.open(final_path).convert("RGBA")
    rgba = np.asarray(final_img, dtype=np.uint8)
    alpha = rgba[..., 3]

    # 2. dark/white/magenta composites
    composites_dir = out_dir / "composites"
    composites_dir.mkdir(parents=True, exist_ok=True)
    for name, bg in COMPOSITE_BACKGROUNDS.items():
        comp = composite_rgb(rgba, bg)
        comp_path = composites_dir / f"composite_{name}.png"
        Image.fromarray(comp, mode="RGB").save(comp_path)
        _record("composite", comp_path, {"background": name})

    # 3. gate D5 crops (if the battery emitted them) — copy verbatim, list every one
    if gate_dir is not None and gate_dir.exists():
        d5_dir = out_dir / "gate_d5_crops"
        battery_path = gate_dir / "battery.json"
        d5_crop_paths: list[str] = []
        if battery_path.exists():
            battery = json.loads(battery_path.read_text())
            d5_crop_paths = battery.get("gates", {}).get("D5_hole_gate", {}).get("crop_paths", [])
        else:
            d5_crop_paths = [str(p) for p in sorted(gate_dir.glob("D5_hole_gate*"))]
        if d5_crop_paths:
            d5_dir.mkdir(parents=True, exist_ok=True)
            for src in d5_crop_paths:
                src_path = Path(src)
                if not src_path.is_absolute():
                    src_path = gate_dir / src_path.name
                if src_path.exists():
                    dst = d5_dir / src_path.name
                    shutil.copy2(src_path, dst)
                    _record("gate_d5_crop", dst)
                else:
                    _record("gate_d5_crop_missing", src_path)

    # 4. deterministic junction/concavity crops at 4x LANCZOS and 12x NEAREST
    points = _alpha_boundary_curvature_points(alpha, n_crops)
    crops_dir = out_dir / "junction_crops"
    if points:
        crops_dir.mkdir(parents=True, exist_ok=True)
    half = crop_size // 2
    for i, (y, x) in enumerate(points):
        tile = _crop_at(final_img, x, y, half)
        lanczos = tile.resize((tile.width * 4, tile.height * 4), Image.LANCZOS)
        nearest = tile.resize((tile.width * 12, tile.height * 12), Image.NEAREST)
        lanczos_path = crops_dir / f"junction_{i:02d}_x{x}_y{y}_4x_lanczos.png"
        nearest_path = crops_dir / f"junction_{i:02d}_x{x}_y{y}_12x_nearest.png"
        lanczos.save(lanczos_path)
        nearest.save(nearest_path)
        _record("junction_crop_4x_lanczos", lanczos_path, {"center_x": x, "center_y": y})
        _record("junction_crop_12x_nearest", nearest_path, {"center_x": x, "center_y": y})

    manifest["n_junction_points"] = len(points)
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--final", required=True, type=Path)
    ap.add_argument("--raw", type=Path, default=None)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--gate-dir", type=Path, default=None)
    ap.add_argument("--n-crops", type=int, default=6)
    ap.add_argument("--crop-size", type=int, default=96)
    args = ap.parse_args(argv)

    manifest = build_review_pack(
        args.final, args.raw, args.out_dir, args.gate_dir, args.n_crops, args.crop_size
    )
    print(json.dumps({"out_dir": str(args.out_dir), "n_files": len(manifest["files"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
