#!/usr/bin/env python3
"""chroma_key.py — production chroma keyer for measured-flat green backgrounds.

Global Lab-distance classification (NOT border-connected flood fill): every
pixel's alpha is a function of its own CIELAB distance to the estimated key
color, so enclosed background-colored pockets die automatically (no flood
walk needed) while pale/translucent art (measured >=11.5 ΔE from the key on
these raws) survives untouched. A boundary-band unmix + despill recovers true
foreground color and removes residual green tint only on the mixed-alpha
rim, so fully-opaque interior pixels (including translucent bubbles) are
never touched.

Usage:
  .venv-gen/bin/python -B scripts/chroma_key.py key IMG.png OUT.png [--json M.json]
  .venv-gen/bin/python -B scripts/chroma_key.py batch RAW1.png [RAW2.png ...] \
      --outdir DIR [--debug-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from skimage.color import rgb2lab

REPO = Path("/Users/za/Documents/product images repo")

# Classification thresholds (CIELAB ΔE to the estimated key color).
# Measured on raw_green_P1: min ΔE bg<->art ~=11.5, but the anti-aliased
# blend ring between them is a CONTINUUM, not a step; a naive DE_OPAQUE=8
# (per the original brief sketch) snaps blend pixels that are still >85%
# green to full alpha=1 before despill ever sees them, producing a visible
# bright-green rim on every branch (measured: rim_a_delta ~ -80 to -100 on
# an 8-threshold run, on-white crops showed the fringe directly). Raising
# DE_OPAQUE to just under the measured 11.5 art/bg floor keeps every
# genuine AA blend pixel inside the soft band long enough for the
# unmix+despill step below to recover it, while true opaque art pixels
# (>=11.5 away) are unaffected.
DE_TRANSPARENT = 3.0   # <= this -> alpha 0 (background)
DE_OPAQUE = 11.0        # >= this -> alpha 1 (art floor, measured min ΔE ~11.5)
DESPILL_CAP = 255.0     # per-channel green reduction in the boundary band (uncapped: full spill removal)

ROIS = {
    "bubble": {"center": (410, 145), "size": (150, 150)},
    "coral_tip": {"center": (560, 110), "size": (170, 170)},
    "seahorse": {"center": (330, 1030), "size": (170, 230)},
    "sand_edge": {"center": (500, 1450), "size": (320, 150)},
}


# ---------------------------------------------------------------------------
# Step 1 — modal key color from the border region
# ---------------------------------------------------------------------------

def estimate_key_color(rgb: np.ndarray, border_frac: float = 0.03) -> np.ndarray:
    h, w = rgb.shape[:2]
    bh, bw = max(2, int(h * border_frac)), max(2, int(w * border_frac))
    strips = [rgb[:bh, :], rgb[-bh:, :], rgb[:, :bw], rgb[:, -bw:]]
    border_px = np.concatenate([s.reshape(-1, 3) for s in strips], axis=0)
    quant = (border_px // 2 * 2)
    uniq, counts = np.unique(quant, axis=0, return_counts=True)
    modal = uniq[np.argmax(counts)].astype(np.float32)
    return modal


# ---------------------------------------------------------------------------
# Step 2 — global Lab-distance classification
# ---------------------------------------------------------------------------

def smoothstep(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def classify_alpha(rgb: np.ndarray, key_rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lab = rgb2lab(rgb.astype(np.float32) / 255.0)
    key_lab = rgb2lab(key_rgb.reshape(1, 1, 3) / 255.0).reshape(3)
    delta_e = np.linalg.norm(lab - key_lab[None, None, :], axis=2)
    alpha = smoothstep((delta_e - DE_TRANSPARENT) / (DE_OPAQUE - DE_TRANSPARENT))
    return alpha, delta_e


# ---------------------------------------------------------------------------
# Step 3 — boundary-band unmix + despill
# ---------------------------------------------------------------------------

def unmix_and_despill(rgb: np.ndarray, alpha: np.ndarray, key_rgb: np.ndarray) -> tuple[np.ndarray, dict]:
    out = rgb.astype(np.float32).copy()
    band = (alpha > 0.02) & (alpha < 0.98)
    a = np.clip(alpha, 1e-3, 1.0)[..., None]
    unmixed = (rgb.astype(np.float32) - (1.0 - a) * key_rgb[None, None, :]) / a
    unmixed = np.clip(unmixed, 0.0, 255.0)
    out[band] = unmixed[band]

    dominant = int(np.argmax(key_rgb))  # 1 == green for #00FF00-style keys

    # A razor-thin classification margin (measured min art/bg ΔE ~11.5) means
    # some AA-blend pixels snap to alpha==1 a couple of px past the true edge
    # while still visibly green (residual rim). Spatial proximity disambiguates
    # them from real interior pale-green/mint art (which sits far from any
    # alpha transition): dilate the transition band 3px and only despill
    # newly-included opaque pixels there IF green is locally in excess.
    dilate_kernel = np.ones((7, 7), np.uint8)
    band_dilated = cv2.dilate(band.astype(np.uint8), dilate_kernel).astype(bool)
    despill_mask = band | band_dilated

    changed = np.zeros(rgb.shape[:2], dtype=np.float32)
    if dominant == 1:
        excess = np.maximum(0.0, out[..., 1] - np.maximum(out[..., 0], out[..., 2]))
        reduction = np.minimum(excess, DESPILL_CAP) * despill_mask
        out[..., 1] -= reduction
        changed = reduction
    else:
        others = [c for c in range(3) if c != dominant]
        excess = np.maximum(0.0, out[..., dominant] - np.minimum(out[..., others[0]], out[..., others[1]]))
        reduction = np.minimum(excess, DESPILL_CAP) * despill_mask
        out[..., dominant] -= reduction
        changed = reduction

    out = np.clip(np.round(out), 0, 255).astype(np.uint8)
    metrics = {
        "band_pixel_count": int(band.sum()),
        "band_frac_of_image": round(float(band.mean()), 5),
        "despill_changed_pixel_count": int((changed > 0).sum()),
        "despill_mean_reduction_on_changed": round(float(changed[changed > 0].mean()), 2) if (changed > 0).any() else 0.0,
        "despill_max_reduction": round(float(changed.max(initial=0.0)), 2),
    }
    return out, metrics


# ---------------------------------------------------------------------------
# Step 5 — gates
# ---------------------------------------------------------------------------

def border_connected_mask(binary: np.ndarray) -> np.ndarray:
    count, labels = cv2.connectedComponents(binary.astype(np.uint8), connectivity=8)
    if count <= 1:
        return np.zeros_like(binary, dtype=bool)
    border_labels = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    border_labels = border_labels[border_labels != 0]
    return np.isin(labels, border_labels)


def enclosed_key_pockets(alpha: np.ndarray, delta_e: np.ndarray, min_area: int = 4, noise_ceiling: int = 50) -> dict:
    """Transparent (alpha<0.5) components not connected to the outer border.

    A dense branching coral has plenty of LEGITIMATE large negative-space
    gaps between forks that never thread back to the frame edge — those are
    correct (background should show through) and are reported separately as
    `legit_hole_count`. The actual defect this gate targets is small speckle
    noise (leftover key-colored dots trapped fully inside otherwise-solid
    paint, the 50-82/image failure of the naive smoothstep keyer): area in
    [min_area, noise_ceiling] px, counted as `noise_pocket_count` — target 0."""
    transparent = alpha < 0.5
    connected = border_connected_mask(transparent)
    residual = transparent & ~connected
    n, labels = cv2.connectedComponents(residual.astype(np.uint8), connectivity=8)
    areas = [int((labels == lbl).sum()) for lbl in range(1, n)]
    areas = [a for a in areas if a >= min_area]
    noise = [a for a in areas if a <= noise_ceiling]
    legit = [a for a in areas if a > noise_ceiling]
    return {
        "noise_pocket_count": len(noise),
        "noise_pocket_max_area": max(noise) if noise else 0,
        "legit_hole_count": len(legit),
        "legit_hole_max_area": max(legit) if legit else 0,
        "total_component_count": len(areas),
    }


def rim_greenness(rgb: np.ndarray, alpha: np.ndarray, band_px: int = 4) -> dict:
    """Band vs interior a*-channel (green<->red axis) delta. Band is
    restricted to the mostly-opaque side of the AA ring (alpha 0.6-0.95) so
    the comparison is object-edge-vs-object-interior, not
    edge-vs-background (which would trivially be huge since the far side of
    every AA ring is still green)."""
    lab = rgb2lab(rgb.astype(np.float32) / 255.0)
    opaque = alpha > 0.98
    transitional = (alpha > 0.6) & (alpha < 0.95)
    if transitional.sum() < 50 or opaque.sum() < 50:
        return {"rim_a_delta": None, "note": "insufficient band/interior pixels"}
    kernel = np.ones((band_px * 2 + 1, band_px * 2 + 1), np.uint8)
    interior = cv2.erode(opaque.astype(np.uint8), kernel).astype(bool) & opaque
    if interior.sum() < 50:
        interior = opaque
    band_a = lab[..., 1][transitional].mean()
    interior_a = lab[..., 1][interior].mean()
    return {
        "rim_a_delta": round(float(band_a - interior_a), 3),
        "band_a_mean": round(float(band_a), 3),
        "interior_a_mean": round(float(interior_a), 3),
        "band_pixel_count": int(transitional.sum()),
        "interior_pixel_count": int(interior.sum()),
    }


def border_occupancy(alpha: np.ndarray, strip: int = 3) -> float:
    h, w = alpha.shape
    mask = np.zeros_like(alpha, dtype=bool)
    mask[:strip, :] = True
    mask[-strip:, :] = True
    mask[:, :strip] = True
    mask[:, -strip:] = True
    return float((alpha[mask] > 0.5).mean())


def run_aura_gate(rgba_path: Path, out_json: Path) -> dict:
    cmd = [sys.executable, str(REPO / "scripts/aura_gate.py"), str(rgba_path), "--json", str(out_json)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if out_json.exists():
        data = json.loads(out_json.read_text())
        entry = data[0] if isinstance(data, list) else data
        return entry
    return {"error": proc.stderr[-500:] if proc.stderr else "aura_gate produced no json"}


# ---------------------------------------------------------------------------
# key() — the whole per-image pipeline
# ---------------------------------------------------------------------------

def key_image(rgb: np.ndarray) -> dict:
    key_rgb = estimate_key_color(rgb)
    alpha, delta_e = classify_alpha(rgb, key_rgb)
    despilled_rgb, despill_metrics = unmix_and_despill(rgb, alpha, key_rgb)
    alpha_u8 = np.clip(np.round(alpha * 255.0), 0, 255).astype(np.uint8)
    rgba = np.dstack([despilled_rgb, alpha_u8])
    return {
        "key_rgb": key_rgb.astype(int).tolist(),
        "alpha": alpha,
        "delta_e": delta_e,
        "rgba": rgba,
        "despill_metrics": despill_metrics,
    }


def compose_bg(rgba: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
    rgb = rgba[..., :3].astype(np.float32)
    a = (rgba[..., 3:4].astype(np.float32)) / 255.0
    bg = np.full_like(rgb, color, dtype=np.float32)
    return np.clip(np.round(rgb * a + bg * (1.0 - a)), 0, 255).astype(np.uint8)


def roi_box(center, size, bounds):
    cx, cy = center
    w, h = size
    x0 = max(0, min(bounds[0] - w, cx - w // 2))
    y0 = max(0, min(bounds[1] - h, cy - h // 2))
    return x0, y0, x0 + w, y0 + h


def save_debug_overlay(rgb: np.ndarray, alpha: np.ndarray, delta_e: np.ndarray, out_path: Path) -> None:
    h, w = alpha.shape
    heat = (np.clip(delta_e / (DE_OPAQUE * 2), 0, 1) * 255).astype(np.uint8)
    heat_color = cv2.applyColorMap(heat, cv2.COLORMAP_TURBO)[..., ::-1]
    band = ((alpha > 0.02) & (alpha < 0.98))
    overlay = heat_color.copy()
    overlay[band] = [255, 0, 255]
    combo = np.concatenate([rgb, heat_color, overlay], axis=1)
    Image.fromarray(combo).save(out_path)


def process_one(raw_path: Path, out_dir: Path, debug_dir: Path) -> dict:
    rgb = np.array(Image.open(raw_path).convert("RGB"))
    result = key_image(rgb)
    tag = raw_path.stem.replace("raw_", "")
    rgba_path = out_dir / f"keyed_{tag}.png"
    Image.fromarray(result["rgba"], mode="RGBA").save(rgba_path)

    magenta_path = out_dir / f"keyed_{tag}_on_magenta.png"
    white_path = out_dir / f"keyed_{tag}_on_white.png"
    Image.fromarray(compose_bg(result["rgba"], (255, 0, 255))).save(magenta_path)
    Image.fromarray(compose_bg(result["rgba"], (255, 255, 255))).save(white_path)

    debug_dir.mkdir(parents=True, exist_ok=True)
    save_debug_overlay(rgb, result["alpha"], result["delta_e"], debug_dir / f"debug_{tag}.png")

    h, w = rgb.shape[:2]
    for roi_name, spec in ROIS.items():
        box = roi_box(spec["center"], spec["size"], (w, h))
        bw, bh = spec["size"]
        scale = 3
        magenta = np.array(Image.open(magenta_path))
        white = np.array(Image.open(white_path))
        label_h = 20
        board = Image.new("RGB", (bw * scale * 2, bh * scale + label_h), (25, 25, 25))
        draw = ImageDraw.Draw(board)
        font = ImageFont.load_default()
        for col, (label, arr) in enumerate((("magenta", magenta), ("white", white))):
            crop = Image.fromarray(arr).crop(box).resize((bw * scale, bh * scale), Image.Resampling.NEAREST)
            board.paste(crop, (col * bw * scale, label_h))
            draw.text((col * bw * scale + 3, 3), f"{tag}/{roi_name}/{label}", fill="white", font=font)
        board.save(debug_dir / f"crop-{tag}-{roi_name}.png")

    pockets = enclosed_key_pockets(result["alpha"], result["delta_e"])
    rim = rim_greenness(result["rgba"][..., :3], result["alpha"])
    occ = border_occupancy(result["alpha"])
    aura_json = debug_dir / f"aura_{tag}.json"
    aura = run_aura_gate(rgba_path, aura_json)

    gates = {
        "raw": str(raw_path),
        "keyed_rgba": str(rgba_path),
        "keyed_on_magenta": str(magenta_path),
        "keyed_on_white": str(white_path),
        "key_rgb": result["key_rgb"],
        "despill": result["despill_metrics"],
        "enclosed_key_pockets": pockets,
        "rim_greenness": rim,
        "border_occupancy_pct": round(occ * 100, 4),
        "aura_gate": aura,
        "verdict": {
            "noise_pockets_ok": pockets["noise_pocket_count"] == 0,
            "border_ok": occ * 100 < 2.0,
        },
    }
    return gates


def cmd_batch(args: argparse.Namespace) -> None:
    out_dir = Path(args.outdir)
    debug_dir = Path(args.debug_dir) if args.debug_dir else out_dir / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_gates = {"entries": []}
    for raw in args.raws:
        raw_path = Path(raw)
        print(f"keying {raw_path.name} ...")
        gates = process_one(raw_path, out_dir, debug_dir)
        all_gates["entries"].append(gates)
        print(f"  pockets={gates['enclosed_key_pockets']} border_occ%={gates['border_occupancy_pct']} "
              f"rim_a_delta={gates['rim_greenness'].get('rim_a_delta')} "
              f"aura={gates['aura_gate'].get('verdict', gates['aura_gate'].get('aura_index'))}")
    gates_path = out_dir / "gates_v3.json"
    gates_path.write_text(json.dumps(all_gates, indent=2))
    print("gates ->", gates_path)


def build_board(gates_path: Path, out_path: Path) -> None:
    gates = json.loads(gates_path.read_text())
    tiles, labels = [], []
    for e in gates["entries"]:
        for bg_name, key in (("magenta", "keyed_on_magenta"), ("white", "keyed_on_white")):
            p = Path(e[key])
            if not p.exists():
                continue
            im = Image.open(p).convert("RGB")
            im.thumbnail((320, 480), Image.LANCZOS)
            tiles.append(im)
            labels.append(f"{Path(e['raw']).stem}/{bg_name}")
    if not tiles:
        return
    pad, label_h = 12, 20
    tw, th = max(t.width for t in tiles), max(t.height for t in tiles)
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    board = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + label_h + pad) + pad), (30, 30, 30))
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    for i, (tile, label) in enumerate(zip(tiles, labels)):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + pad), pad + r * (th + label_h + pad)
        board.paste(tile, (x, y))
        draw.text((x, y + th + 2), label, fill=(255, 255, 255), font=font)
    board.save(out_path)
    print("board ->", out_path)


def cmd_key(args: argparse.Namespace) -> None:
    rgb = np.array(Image.open(args.image).convert("RGB"))
    result = key_image(rgb)
    Image.fromarray(result["rgba"], mode="RGBA").save(args.out)
    print(f"keyed -> {args.out}  key_rgb={result['key_rgb']}")
    if args.json:
        Path(args.json).write_text(json.dumps({
            "key_rgb": result["key_rgb"],
            "despill_metrics": result["despill_metrics"],
        }, indent=2))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_key = sub.add_parser("key")
    p_key.add_argument("image")
    p_key.add_argument("out")
    p_key.add_argument("--json")
    p_key.set_defaults(func=cmd_key)

    p_batch = sub.add_parser("batch")
    p_batch.add_argument("raws", nargs="+")
    p_batch.add_argument("--outdir", required=True)
    p_batch.add_argument("--debug-dir", default=None)
    p_batch.set_defaults(func=cmd_batch)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
