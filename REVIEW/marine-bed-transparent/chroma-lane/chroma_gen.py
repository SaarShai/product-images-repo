#!/usr/bin/env python3
"""chroma_gen.py — gpt-image-2 uniform-key-background matrix experiment.

Generates 3 colors x 3 prompt-hygiene styles (9 gens) via the OpenAI Responses
API async `background: true` image_generation tool (gpt-image-2 rejects
background=transparent AND its images/edits sync call exceeds the ~60-75s cap
at quality=high — both confirmed live before writing this script), then keys
each result and scores 3 gates: bg-uniformity, bg-vs-art color separation, and
post-key rim-halo / border-occupancy / enclosed-pocket cleanliness.

Usage:
  .venv-gen/bin/python -B chroma_gen.py gen      # submit + poll + save raws
  .venv-gen/bin/python -B chroma_gen.py gate     # key + score all raws
  .venv-gen/bin/python -B chroma_gen.py board    # build contact board
  .venv-gen/bin/python -B chroma_gen.py all
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFont
from skimage.color import rgb2lab

REPO = Path("/Users/za/Documents/product images repo")
sys.path.insert(0, str(REPO / "scripts"))
from _falcommon import load_openai_key  # noqa: E402

SOURCE = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_20_05 AM.png"
)
OUT_DIR = REPO / "REVIEW/marine-bed-transparent/chroma-lane"
RAW_DIR = OUT_DIR / "raws"
KEYED_DIR = OUT_DIR / "keyed"
GATES_PATH = OUT_DIR / "chroma_gates.json"

MODEL = "gpt-image-2"
SIZE = "1024x1536"
QUALITY = "high"

COLORS = {
    "green": "#00FF00",
    "magenta": "#FF00FF",
    "azure": "#00A0FF",
}

EDGE_HYGIENE_BLOCK = (
    "every object has clearly defined, fully closed outlines; no shape fades "
    "into the background; edges crisp; interior highlights enclosed by "
    "visible outlines"
)


def build_prompt(hex_color: str, style: str) -> str:
    base = (
        f"Keep this illustration's artwork completely unchanged — same subject, "
        f"composition, colors, and detail — and repaint ONLY the background to "
        f"be completely solid, flat, uniform color {hex_color}. Every single "
        f"background pixel must be the identical RGB value {hex_color}. No "
        f"gradient, no vignette, no texture, no shadow, no glow."
    )
    if style == "P1":
        return base
    studio = (
        " Professional chroma-key studio backdrop, as used for green-screen "
        "compositing; the artwork floats on the flat key color; no reflection "
        "or color spill onto the artwork."
    )
    return base + studio


def build_prompt_p3(hex_color: str) -> str:
    base = build_prompt(hex_color, "P2")
    return (
        base
        + f" {EDGE_HYGIENE_BLOCK}."
        + " No glow, aura, halo, soft wash, or gradient bloom around the "
        "artwork; background color runs right up to the crisp painted edge "
        "of every element."
        + " The entire illustration fits fully inside the frame with clear "
        "margins on all sides; nothing cropped at any edge."
    )


def prompt_for(hex_color: str, style: str) -> str:
    if style == "P3":
        return build_prompt_p3(hex_color)
    return build_prompt(hex_color, style)


def submit_job(key: str, prompt: str) -> str:
    b64 = base64.b64encode(SOURCE.read_bytes()).decode()
    payload = {
        "model": "gpt-5",
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": f"data:image/png;base64,{b64}"},
                ],
            }
        ],
        "tools": [
            {"type": "image_generation", "model": MODEL, "quality": QUALITY, "size": SIZE}
        ],
        "background": True,
    }
    r = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"submit failed HTTP {r.status_code}: {r.text[:500]}")
    return r.json()["id"]


def poll_job(key: str, resp_id: str, timeout_s: int = 600) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        r = requests.get(
            f"https://api.openai.com/v1/responses/{resp_id}",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
        j = r.json()
        status = j.get("status")
        if status in ("completed", "failed", "cancelled", "incomplete"):
            return j
        time.sleep(5)
    raise TimeoutError(f"job {resp_id} did not complete within {timeout_s}s")


def extract_image_b64(job: dict) -> str | None:
    for item in job.get("output", []):
        if item.get("type") == "image_generation_call" and item.get("result"):
            return item["result"]
    return None


def cmd_gen():
    key = load_openai_key()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"source": str(SOURCE), "model": MODEL, "size": SIZE, "quality": QUALITY, "entries": []}
    jobs = []
    for color_name, hex_color in COLORS.items():
        for style in ("P1", "P2", "P3"):
            prompt = prompt_for(hex_color, style)
            t0 = time.time()
            resp_id = submit_job(key, prompt)
            jobs.append({"color": color_name, "hex": hex_color, "style": style, "resp_id": resp_id, "t0": t0, "prompt": prompt})
            print(f"submitted {color_name}/{style} -> {resp_id}")

    for j in jobs:
        print(f"polling {j['color']}/{j['style']} ({j['resp_id']}) ...")
        job = poll_job(key, j["resp_id"])
        dur = round(time.time() - j["t0"], 1)
        entry = {
            "color": j["color"], "hex": j["hex"], "style": j["style"],
            "resp_id": j["resp_id"], "duration_s": dur, "status": job.get("status"),
            "prompt": j["prompt"],
        }
        b64img = extract_image_b64(job)
        if b64img:
            out_path = RAW_DIR / f"raw_{j['color']}_{j['style']}.png"
            out_path.write_bytes(base64.b64decode(b64img))
            entry["path"] = str(out_path)
            entry["error"] = None
        else:
            entry["path"] = None
            entry["error"] = job.get("error") or "no image_generation_call result in output"
        print(f"  -> {entry['status']} in {dur}s {'OK' if entry['path'] else 'FAILED: ' + str(entry['error'])}")
        manifest["entries"].append(entry)
        (OUT_DIR / "gen_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("gen done ->", OUT_DIR / "gen_manifest.json")


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

def parse_hex(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return np.array([int(value[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def border_connected_mask(binary: np.ndarray) -> np.ndarray:
    count, labels = cv2.connectedComponents(binary.astype(np.uint8), connectivity=8)
    if count <= 1:
        return np.zeros_like(binary, dtype=bool)
    border_labels = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    border_labels = border_labels[border_labels != 0]
    return np.isin(labels, border_labels)


def delta_e(lab_a: np.ndarray, lab_b: np.ndarray) -> np.ndarray:
    return np.linalg.norm(lab_a - lab_b, axis=-1)


def gate_uniformity(rgb: np.ndarray, key_hex: str) -> dict:
    """Modal-color share + ΔE<3 fraction + std over the border-connected bg region."""
    key = parse_hex(key_hex)
    dist_to_key = np.linalg.norm(rgb.astype(np.float32) - key[None, None, :], axis=2)
    # bg candidate = pixels reasonably near the key color, then keep border-connected component
    candidate = dist_to_key < 60.0
    bg_mask = border_connected_mask(candidate)
    if bg_mask.sum() < 100:
        return {"bg_pixel_count": int(bg_mask.sum()), "insufficient_bg": True}
    bg_rgb = rgb[bg_mask]
    # modal value: round to nearest 4 to bucket sensor noise, then take most common
    quant = (bg_rgb // 4 * 4)
    uniq, counts = np.unique(quant, axis=0, return_counts=True)
    modal = uniq[np.argmax(counts)].astype(np.float32)
    modal_share = float(counts.max() / bg_rgb.shape[0])
    lab_bg = rgb2lab(bg_rgb.reshape(1, -1, 3).astype(np.float32) / 255.0).reshape(-1, 3)
    lab_modal = rgb2lab(modal.reshape(1, 1, 3) / 255.0).reshape(3)
    de = delta_e(lab_bg, lab_modal[None, :])
    frac_de_lt3 = float((de < 3.0).mean())
    std_rgb = [float(bg_rgb[:, c].std()) for c in range(3)]
    return {
        "bg_pixel_count": int(bg_mask.sum()),
        "bg_frac_of_image": round(float(bg_mask.mean()), 4),
        "modal_rgb": modal.astype(int).tolist(),
        "modal_share": round(modal_share, 4),
        "frac_deltaE_lt3": round(frac_de_lt3, 4),
        "bg_rgb_std": [round(v, 2) for v in std_rgb],
        "insufficient_bg": False,
    }, bg_mask, modal


def gate_separation(rgb: np.ndarray, bg_mask: np.ndarray, modal_rgb: np.ndarray) -> dict:
    """Min ΔE between modal bg color and dominant art-pixel clusters (k-means, k=6)."""
    art_mask = ~bg_mask
    art_rgb = rgb[art_mask]
    if art_rgb.shape[0] < 100:
        return {"min_deltaE_to_art_clusters": None, "note": "insufficient art pixels"}
    sample = art_rgb[np.random.RandomState(0).choice(art_rgb.shape[0], size=min(20000, art_rgb.shape[0]), replace=False)]
    k = 6
    Z = sample.astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5)
    _, labels, centers = cv2.kmeans(Z, k, None, criteria, 4, cv2.KMEANS_PP_CENTERS)
    lab_centers = rgb2lab(centers.reshape(1, -1, 3) / 255.0).reshape(-1, 3)
    lab_modal = rgb2lab(modal_rgb.reshape(1, 1, 3) / 255.0).reshape(3)
    des = delta_e(lab_centers, lab_modal[None, :])
    return {
        "min_deltaE_to_art_clusters": round(float(des.min()), 2),
        "cluster_centers_rgb": centers.astype(int).tolist(),
        "cluster_deltaE": [round(float(d), 2) for d in des],
    }


def key_alpha(rgb: np.ndarray, key: np.ndarray, radius_transparent=30.0, radius_opaque=100.0):
    dist = np.linalg.norm(rgb.astype(np.float32) - key[None, None, :], axis=2)
    t = np.clip((dist - radius_transparent) / (radius_opaque - radius_transparent), 0.0, 1.0)
    alpha = t * t * (3.0 - 2.0 * t)
    return alpha, dist


def rim_halo_metric(rgb: np.ndarray, alpha: np.ndarray, band_px: int = 4) -> dict:
    """Compare mean color of the semi-transparent edge BAND vs the fully-opaque
    INTERIOR just inside it. A large luminance/saturation jump signals a halo
    or color-spill ring left by the key."""
    opaque = alpha > 0.98
    transitional = (alpha > 0.02) & (alpha < 0.98)
    if transitional.sum() < 50 or opaque.sum() < 50:
        return {"rim_index": None, "note": "insufficient band/interior pixels"}
    kernel = np.ones((band_px * 2 + 1, band_px * 2 + 1), np.uint8)
    interior = cv2.erode(opaque.astype(np.uint8), kernel).astype(bool) & opaque
    if interior.sum() < 50:
        interior = opaque
    band_lab = rgb2lab(rgb[transitional].reshape(1, -1, 3).astype(np.float32) / 255.0).reshape(-1, 3)
    interior_lab = rgb2lab(rgb[interior].reshape(1, -1, 3).astype(np.float32) / 255.0).reshape(-1, 3)
    band_mean = band_lab.mean(axis=0)
    interior_mean = interior_lab.mean(axis=0)
    rim_index = float(np.linalg.norm(band_mean - interior_mean))
    return {
        "rim_index": round(rim_index, 3),
        "band_px": band_px,
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


def enclosed_pockets(alpha: np.ndarray, thresh=0.5) -> dict:
    """Count fully-enclosed (non-border-connected) background pockets trapped
    inside the foreground alpha — signals a noisy/broken key mask."""
    transparent = alpha < thresh
    n, labels = cv2.connectedComponents((~transparent).astype(np.uint8) * 0 + transparent.astype(np.uint8), connectivity=8)
    if n <= 1:
        return {"enclosed_pocket_count": 0, "enclosed_pocket_max_area": 0}
    border_labels = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])).tolist())
    areas = []
    for lbl in range(1, n):
        if lbl in border_labels:
            continue
        areas.append(int((labels == lbl).sum()))
    return {
        "enclosed_pocket_count": len(areas),
        "enclosed_pocket_max_area": max(areas) if areas else 0,
    }


def cmd_gate():
    manifest_path = OUT_DIR / "gen_manifest.json"
    if not manifest_path.exists():
        print("no gen_manifest.json — run `gen` first", file=sys.stderr)
        sys.exit(1)
    manifest = json.loads(manifest_path.read_text())
    KEYED_DIR.mkdir(parents=True, exist_ok=True)
    gates = {"entries": []}
    for e in manifest["entries"]:
        if not e.get("path") or not Path(e["path"]).exists():
            gates["entries"].append({**e, "gate_error": "no raw image"})
            continue
        rgb = np.array(Image.open(e["path"]).convert("RGB"))
        key = parse_hex(e["hex"])
        uni = gate_uniformity(rgb, e["hex"])
        if isinstance(uni, tuple):
            uni_metrics, bg_mask, modal = uni
        else:
            uni_metrics, bg_mask, modal = uni, None, None
        entry = dict(e)
        entry["uniformity"] = uni_metrics
        if bg_mask is not None:
            entry["separation"] = gate_separation(rgb, bg_mask, modal)
        else:
            entry["separation"] = {"note": "skipped, insufficient bg"}

        alpha, _ = key_alpha(rgb, key)
        keyed = np.dstack([rgb, (alpha * 255).astype(np.uint8)])
        keyed_path = KEYED_DIR / f"keyed_{e['color']}_{e['style']}.png"
        Image.fromarray(keyed, mode="RGBA").save(keyed_path)
        entry["keyed_path"] = str(keyed_path)
        entry["rim_halo"] = rim_halo_metric(rgb, alpha)
        entry["border_occupancy_pct"] = round(border_occupancy(alpha) * 100, 3)
        entry["enclosed"] = enclosed_pockets(alpha)
        gates["entries"].append(entry)
        print(f"gated {e['color']}/{e['style']}")
    GATES_PATH.write_text(json.dumps(gates, indent=2))
    print("gates ->", GATES_PATH)


def cmd_board():
    if not GATES_PATH.exists():
        print("no chroma_gates.json — run `gate` first", file=sys.stderr)
        sys.exit(1)
    gates = json.loads(GATES_PATH.read_text())
    tiles, labels = [], []
    for e in gates["entries"]:
        kp = e.get("keyed_path")
        if not kp or not Path(kp).exists():
            continue
        im = Image.open(kp).convert("RGBA")
        im.thumbnail((360, 540), Image.LANCZOS)
        magenta = Image.new("RGBA", im.size, (255, 0, 255, 255))
        comp = Image.alpha_composite(magenta, im).convert("RGB")
        tiles.append(comp)
        labels.append(f"{e['color']}/{e['style']}")
    if not tiles:
        print("no keyed tiles to board")
        return
    pad, label_h = 12, 24
    tw, th = max(t.width for t in tiles), max(t.height for t in tiles)
    cols = 3
    rows = (len(tiles) + cols - 1) // cols
    board = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + label_h + pad) + pad), (30, 30, 30))
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default()
    for i, (tile, label) in enumerate(zip(tiles, labels)):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + pad), pad + r * (th + label_h + pad)
        board.paste(tile, (x, y))
        draw.text((x, y + th + 4), label, fill=(255, 255, 255), font=font)
    board_path = OUT_DIR / "BOARD-chroma-lane-magenta.png"
    board.save(board_path)
    print("board ->", board_path)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd in ("gen", "all"):
        cmd_gen()
    if cmd in ("gate", "all"):
        cmd_gate()
    if cmd in ("board", "all"):
        cmd_board()


if __name__ == "__main__":
    main()
