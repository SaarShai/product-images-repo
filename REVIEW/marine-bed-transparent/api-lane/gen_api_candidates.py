#!/usr/bin/env python3
"""gen_api_candidates.py — API-lane transparent coral-tower candidates.

Calls the OpenAI images/edits endpoint (falls back to images/generations if a
model rejects edits) with background=transparent, quality=high, size=1024x1536,
for two models x two independent calls each (no seed param exposed by the
Images API, so "seed" == independent call index). Saves raw PNGs + a
per-call gates entry (mode, transparent%, checkerboard check, border alpha
occupancy) to gates.json, and a magenta-composited contact-sheet BOARD.

Usage:
  .venv-gen/bin/python -B gen_api_candidates.py
"""
import base64
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
import requests
from PIL import Image

REPO = Path("/Users/za/Documents/product images repo")
sys.path.insert(0, str(REPO / "scripts"))
from _falcommon import load_openai_key  # noqa: E402

SOURCE = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_20_05 AM.png"
)
OUT_DIR = REPO / "REVIEW/marine-bed-transparent/api-lane"
PROMPT_PATH = OUT_DIR / "PROMPT-coral-tower-transparent.md"

MODELS = ["gpt-image-1.5", "chatgpt-image-latest"]
CALLS_PER_MODEL = 2
SIZE = "1024x1536"
QUALITY = "high"


def call_edit(model: str, key: str, prompt: str):
    with SOURCE.open("rb") as fh:
        img_bytes = fh.read()
    files = {"image": ("source.png", img_bytes, "image/png")}
    data = {
        "model": model,
        "prompt": prompt,
        "n": "1",
        "size": SIZE,
        "quality": QUALITY,
        "background": "transparent",
    }
    r = requests.post(
        "https://api.openai.com/v1/images/edits",
        headers={"Authorization": f"Bearer {key}"},
        files=files, data=data, timeout=300,
    )
    return r


def call_generate(model: str, key: str, prompt: str):
    data = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": SIZE,
        "quality": QUALITY,
        "background": "transparent",
    }
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=data, timeout=300,
    )
    return r


def checkerboard_probe(rgb: np.ndarray, alpha: np.ndarray) -> dict:
    """Sample presumed-background (alpha>=250, i.e. claimed-opaque) pixels for the
    known ChatGPT-web fake-transparency checker signature (~254/246 alternating
    near-white tiles). Returns detection flag + stats."""
    opaque_bg_mask = alpha >= 250
    # restrict to corner/edge regions likely to be "background" rather than subject
    h, w = alpha.shape
    corner = np.zeros_like(opaque_bg_mask)
    m = max(4, min(h, w) // 8)
    corner[:m, :] = True
    corner[-m:, :] = True
    corner[:, :m] = True
    corner[:, -m:] = True
    region = opaque_bg_mask & corner
    n = int(region.sum())
    if n < 50:
        return {"checker_detected": False, "sampled_px": n, "note": "too few opaque border px to judge"}
    vals = rgb[region]
    near_white = ((vals >= 235) & (vals <= 255)).all(axis=1)
    frac_near_white = float(near_white.mean())
    # look for two-cluster near-white signature (e.g. 254 vs 246) with real variance
    if near_white.sum() > 20:
        graylevels = vals[near_white].mean(axis=1)
        std = float(graylevels.std())
        rng = float(graylevels.max() - graylevels.min())
    else:
        std, rng = 0.0, 0.0
    checker = bool(frac_near_white > 0.6 and 2.0 < std < 20.0 and rng > 3)
    return {
        "checker_detected": checker,
        "sampled_px": n,
        "frac_near_white_in_opaque_border": round(frac_near_white, 4),
        "graylevel_std": round(std, 3),
        "graylevel_range": round(rng, 3),
    }


def border_occupancy(alpha: np.ndarray, strip: int = 3) -> float:
    h, w = alpha.shape
    mask = np.zeros_like(alpha, dtype=bool)
    mask[:strip, :] = True
    mask[-strip:, :] = True
    mask[:, :strip] = True
    mask[:, -strip:] = True
    occupied = alpha[mask] >= 10
    return float(occupied.mean())


def analyze(path: Path) -> dict:
    im = Image.open(path)
    mode = im.mode
    result = {"mode": mode, "width": im.width, "height": im.height}
    if mode != "RGBA":
        result.update({
            "is_rgba": False,
            "transparent_pct": None,
            "checker": {"checker_detected": None, "note": "not RGBA, no alpha channel"},
            "border_occupancy_pct": None,
        })
        return result
    arr = np.array(im.convert("RGBA"))
    rgb = arr[..., :3].astype(np.int32)
    alpha = arr[..., 3].astype(np.int32)
    transparent_frac = float((alpha < 10).mean())
    result["is_rgba"] = True
    result["transparent_pct"] = round(transparent_frac * 100, 2)
    result["checker"] = checkerboard_probe(rgb, alpha)
    result["border_occupancy_pct"] = round(border_occupancy(alpha) * 100, 3)
    return result


def save_from_response(r: requests.Response, out_path: Path) -> dict:
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:1000]}"}
    j = r.json()
    b64 = j["data"][0]["b64_json"]
    raw = base64.b64decode(b64)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw)
    return {"usage": j.get("usage", {})}


def make_board(entries, board_path: Path):
    tiles = []
    labels = []
    for e in entries:
        p = Path(e["path"])
        if not p.exists():
            continue
        im = Image.open(p).convert("RGBA")
        im.thumbnail((480, 720), Image.LANCZOS)
        magenta = Image.new("RGBA", im.size, (255, 0, 255, 255))
        composited = Image.alpha_composite(magenta, im)
        tiles.append(composited.convert("RGB"))
        labels.append(f"{e['model']} seed{e['seed_idx']}")
    if not tiles:
        return
    pad = 16
    label_h = 28
    tile_w = max(t.width for t in tiles)
    tile_h = max(t.height for t in tiles)
    cols = min(4, len(tiles))
    rows = (len(tiles) + cols - 1) // cols
    board_w = cols * (tile_w + pad) + pad
    board_h = rows * (tile_h + label_h + pad) + pad
    board = Image.new("RGB", (board_w, board_h), (30, 30, 30))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(board)
    for i, (tile, label) in enumerate(zip(tiles, labels)):
        r, c = divmod(i, cols)
        x = pad + c * (tile_w + pad)
        y = pad + r * (tile_h + label_h + pad)
        board.paste(tile, (x, y))
        draw.text((x, y + tile_h + 4), label, fill=(255, 255, 255))
    board.save(board_path)


def main():
    key = load_openai_key()
    prompt = PROMPT_PATH.read_text()
    gates = {"source": str(SOURCE), "size": SIZE, "quality": QUALITY, "entries": []}

    for model in MODELS:
        for seed_idx in range(1, CALLS_PER_MODEL + 1):
            out_path = OUT_DIR / f"api-{model.replace('.', '_')}-seed{seed_idx}.png"
            entry = {"model": model, "seed_idx": seed_idx, "path": str(out_path)}
            t0 = time.time()
            try:
                r = call_edit(model, key, prompt)
                entry["endpoint_tried"] = ["edits"]
                if r.status_code != 200:
                    entry["edits_error"] = f"HTTP {r.status_code}: {r.text[:1000]}"
                    print(f"[{model} seed{seed_idx}] edits failed: {entry['edits_error']}", file=sys.stderr)
                    print(f"[{model} seed{seed_idx}] falling back to generations", file=sys.stderr)
                    r2 = call_generate(model, key, prompt)
                    entry["endpoint_tried"].append("generations")
                    save_res = save_from_response(r2, out_path)
                    entry["endpoint_used"] = "generations" if "error" not in save_res else None
                else:
                    save_res = save_from_response(r, out_path)
                    entry["endpoint_used"] = "edits" if "error" not in save_res else None
            except requests.exceptions.RequestException as exc:
                save_res = {"error": f"{type(exc).__name__}: {exc}"}
                entry["endpoint_used"] = None
            entry["duration_s"] = round(time.time() - t0, 1)
            entry.update(save_res)
            if out_path.exists():
                entry["analysis"] = analyze(out_path)
            print(f"[{model} seed{seed_idx}] done in {entry['duration_s']}s -> "
                  f"{'OK' if out_path.exists() else 'FAILED'}")
            gates["entries"].append(entry)
            (OUT_DIR / "gates.json").write_text(json.dumps(gates, indent=2))

    make_board(
        [e for e in gates["entries"] if Path(e["path"]).exists()],
        OUT_DIR / "BOARD-api-lane-magenta.png",
    )
    (OUT_DIR / "gates.json").write_text(json.dumps(gates, indent=2))
    print("DONE. gates.json + BOARD-api-lane-magenta.png written.")


if __name__ == "__main__":
    main()
