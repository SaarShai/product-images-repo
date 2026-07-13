#!/usr/bin/env python3
"""Round-4: latest non-alpha models on a FLAT KEY BACKGROUND (R21).

gpt-image-2 proper rejects background=transparent (round-1 canary), so the
route is: generate on a perfectly flat solid key background with the SAME
rich style + thick closed non-AA contours validated in rounds 1-3, then
remove the background pixels with chroma_key.py. Round-1's green leak was
with the old thin-edge prompt; hypothesis: bold dark closed outlines make
keying reliable.

Cells: gpt-image-2 x {GREEN #00FF00, MAGENTA #FF00FF} x 2 reps, HARD edge.
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROUND_DIR = Path(__file__).resolve().parent
RAW_DIR = ROUND_DIR / "raws"
PROMPT_DIR = ROUND_DIR / "prompts"
MANIFEST_PATH = ROUND_DIR / "MANIFEST.json"

sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tasks" / "transparent-bg-endgame" / "round3_rich"))
from _falcommon import load_openai_key  # noqa: E402
from gen_round3 import (  # noqa: E402
    EXCLUSIONS_BLOCK,
    HARD_EDGE_BLOCK,
    KEYABLE_BLOCK,
    RICH_STYLE_BLOCK,
    SUBJECT_BLOCK,
    THICK_CONTOUR_BLOCK,
)

SIZE = "1024x1536"
QUALITY = "high"
RESPONSES_ENDPOINT = "https://api.openai.com/v1/responses"
GEN_MODEL = "gpt-image-2"
REPS = 2

BG_SPECS = {
    "GREEN": ("#00FF00", "pure bright chroma green (#00FF00)"),
    "MAGENTA": ("#FF00FF", "pure bright magenta (#FF00FF)"),
}


def key_bg_block(desc: str) -> str:
    return (
        "[BACKGROUND - FLAT KEY]\n"
        f"The entire background is a single perfectly flat, uniform field of "
        f"{desc} - one exact solid color across every background pixel. "
        "Absolutely no gradient, vignette, texture, paper grain, noise, "
        "lighting variation, or shadow anywhere in the background. The "
        "background color must never appear inside the subject: no colored "
        "reflections, color spill, rim light, or ambient tint from the "
        "background onto the artwork. The subject's outermost bold ink "
        "contour meets the flat background color abruptly, with no glow, "
        "halo, aura, wash, bloom, mist, drop shadow, contact shadow, ground "
        "plane, or soft transition band around the silhouette. No sand, "
        "seabed, rock base, or any surface; the subject floats on the flat "
        "color field. Gaps between branches show only the flat background "
        "color, never pale paint."
    )


def build_prompt(bg_desc: str) -> str:
    return "\n\n".join(
        [
            SUBJECT_BLOCK,
            RICH_STYLE_BLOCK,
            THICK_CONTOUR_BLOCK,
            KEYABLE_BLOCK,
            EXCLUSIONS_BLOCK,
            key_bg_block(bg_desc),
            HARD_EDGE_BLOCK,
        ]
    )


def submit(key: str, prompt: str) -> str:
    import requests

    payload = {
        "model": "gpt-5",
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        "tools": [
            {"type": "image_generation", "model": GEN_MODEL, "quality": QUALITY, "size": SIZE}
        ],
        "background": True,
    }
    resp = requests.post(
        RESPONSES_ENDPOINT,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"submit failed HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json()["id"]


def poll(key: str, response_id: str, timeout_s: int = 900) -> dict:
    import requests

    t0 = time.time()
    while time.time() - t0 < timeout_s:
        job = requests.get(
            f"{RESPONSES_ENDPOINT}/{response_id}",
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        ).json()
        if job.get("status") in ("completed", "failed", "cancelled", "incomplete"):
            return job
        time.sleep(5)
    raise TimeoutError(f"job {response_id} timed out after {timeout_s}s")


def extract_b64(job: dict) -> str | None:
    for item in job.get("output", []):
        if item.get("type") == "image_generation_call" and item.get("result"):
            return item["result"]
    return None


def bg_flatness(path: Path, hexcolor: str) -> dict:
    """Measure how close border-region pixels are to the requested key color."""
    from PIL import Image
    import numpy as np

    target = tuple(int(hexcolor[i : i + 2], 16) for i in (1, 3, 5))
    with Image.open(path) as img:
        arr = np.asarray(img.convert("RGB"), dtype=np.int16)
    border = np.concatenate(
        [arr[:8].reshape(-1, 3), arr[-8:].reshape(-1, 3), arr[:, :8].reshape(-1, 3), arr[:, -8:].reshape(-1, 3)]
    )
    dist = np.abs(border - np.array(target)).sum(axis=1)
    return {
        "border_within_30": round(float((dist <= 30).mean()), 4),
        "border_median_dist": int(np.median(dist)),
    }


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    key = load_openai_key()
    manifest = {"experiment": "round4_key", "model": GEN_MODEL, "size": SIZE, "quality": QUALITY, "entries": []}

    for bg_id, (hexcolor, desc) in BG_SPECS.items():
        prompt = build_prompt(desc)
        (PROMPT_DIR / f"key_{bg_id}.txt").write_text(prompt + "\n")
        for rep in range(1, REPS + 1):
            cell = f"H-G2-{bg_id}-r{rep}"
            out = RAW_DIR / f"{cell}.png"
            entry = {"id": cell, "bg": bg_id, "key_hex": hexcolor, "status": "pending"}
            if out.exists():
                entry["status"] = "skipped_existing"
                manifest["entries"].append(entry)
                print(f"SKIP {cell}")
                continue
            t0 = time.time()
            try:
                rid = submit(key, prompt)
                entry["response_id"] = rid
                job = poll(key, rid)
                b64 = extract_b64(job)
                if not b64:
                    raise RuntimeError(f"no image result: {job.get('error') or job.get('status')}")
                out.write_bytes(base64.b64decode(b64))
                entry["wall_secs"] = round(time.time() - t0, 1)
                entry["bg_flatness"] = bg_flatness(out, hexcolor)
                entry["status"] = "ok"
                print(f"OK   {cell} ({entry['wall_secs']}s) flat={entry['bg_flatness']}")
            except Exception as exc:  # noqa: BLE001
                entry["status"] = "error"
                entry["error"] = str(exc)
                print(f"ERR  {cell}: {exc}", file=sys.stderr)
            manifest["entries"].append(entry)
            MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
