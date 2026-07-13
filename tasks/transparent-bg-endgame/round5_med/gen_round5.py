#!/usr/bin/env python3
"""Round-5: R22 — medium outline weight (round-4 'excessive' verdict), green key only."""
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
sys.path.insert(0, str(REPO / "tasks" / "transparent-bg-endgame" / "round4_key"))
from _falcommon import load_openai_key  # noqa: E402
from gen_round3 import (  # noqa: E402
    EXCLUSIONS_BLOCK,
    HARD_EDGE_BLOCK,
    KEYABLE_BLOCK,
    RICH_STYLE_BLOCK,
    SUBJECT_BLOCK,
)
from gen_round4 import BG_SPECS, bg_flatness, extract_b64, key_bg_block, poll, submit  # noqa: E402

SIZE = "1024x1536"
REPS = 2

MEDIUM_CONTOUR_BLOCK = (
    "[EDGE CONTOUR - MEDIUM]\n"
    "Every painted shape is enclosed by a continuous, fully closed ink "
    "contour with no gaps or fade-outs - a clean, confident outline of "
    "MEDIUM weight, about the width of a fine felt-tip pen: clearly visible "
    "and crisp, but slender and elegant, never chunky or heavy. The contour "
    "color is a clearly darker, more saturated version of the adjacent local "
    "fill - never pure black and never white. The outermost silhouette "
    "outline may be slightly firmer than interior lines, but stays a slim, "
    "refined line. Every white-looking subject detail or highlight is a "
    "visibly tinted pastel off-white, fully enclosed by its contour."
)


def build_prompt(bg_desc: str) -> str:
    return "\n\n".join(
        [
            SUBJECT_BLOCK,
            RICH_STYLE_BLOCK,
            MEDIUM_CONTOUR_BLOCK,
            KEYABLE_BLOCK,
            EXCLUSIONS_BLOCK,
            key_bg_block(bg_desc),
            HARD_EDGE_BLOCK,
        ]
    )


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    key = load_openai_key()
    hexcolor, desc = BG_SPECS["GREEN"]
    prompt = build_prompt(desc)
    (PROMPT_DIR / "med_GREEN.txt").write_text(prompt + "\n")
    manifest = {"experiment": "round5_med", "model": "gpt-image-2", "entries": []}
    for rep in range(1, REPS + 1):
        cell = f"H-G2-MED-GREEN-r{rep}"
        out = RAW_DIR / f"{cell}.png"
        entry = {"id": cell, "key_hex": hexcolor, "status": "pending"}
        if out.exists():
            entry["status"] = "skipped_existing"
            manifest["entries"].append(entry)
            continue
        t0 = time.time()
        try:
            rid = submit(key, prompt)
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
