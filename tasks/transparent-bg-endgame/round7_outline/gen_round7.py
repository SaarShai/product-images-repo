#!/usr/bin/env python3
"""Round-7: R27 — enforce the significant-but-not-thick outline.

Round-6 verdict: model under-painted the medium outlines (soft coral edges,
no visible ink contour), so edge blend pixels sit on coral color and read as
stray green/olive. Restore a clearly VISIBLE dark contour at every silhouette
so blend pixels land on ink. Same no-filament + no-green-art + green key.
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
sys.path.insert(0, str(REPO / "tasks" / "transparent-bg-endgame" / "round4_key"))
sys.path.insert(0, str(REPO / "tasks" / "transparent-bg-endgame" / "round6_clean"))
from _falcommon import load_openai_key  # noqa: E402
from gen_round3 import EXCLUSIONS_BLOCK, HARD_EDGE_BLOCK, RICH_STYLE_BLOCK  # noqa: E402
from gen_round4 import BG_SPECS, bg_flatness, extract_b64, key_bg_block, poll, submit  # noqa: E402
from gen_round6 import NO_FILAMENT_BLOCK, NO_GREEN_ART_BLOCK, SUBJECT_BLOCK_V2  # noqa: E402

REPS = 2

SIGNIFICANT_CONTOUR_BLOCK = (
    "[EDGE CONTOUR - SIGNIFICANT, MANDATORY]\n"
    "This is a NON-NEGOTIABLE style requirement: every shape in the artwork "
    "is enclosed by a clearly VISIBLE, continuous, fully closed dark ink "
    "contour line - like classic pen-and-ink illustration with watercolor "
    "fill. The line is slim and elegant (fine felt-tip weight, never chunky), "
    "but it must be DARK and OBVIOUS at a glance: a deep, saturated, darker "
    "shade of the adjacent fill color, never faded, never soft, never "
    "blended away. The outermost silhouette of the whole subject carries the "
    "most defined, unbroken line in the image; if any part of the silhouette "
    "lacks a visible dark contour line the image is wrong. No open, soft, or "
    "lineless watercolor edges anywhere."
)


def build_prompt(bg_desc: str) -> str:
    return "\n\n".join(
        [
            SUBJECT_BLOCK_V2,
            RICH_STYLE_BLOCK,
            SIGNIFICANT_CONTOUR_BLOCK,
            NO_FILAMENT_BLOCK,
            NO_GREEN_ART_BLOCK,
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
    (PROMPT_DIR / "outline_GREEN.txt").write_text(prompt + "\n")
    manifest = {"experiment": "round7_outline", "model": "gpt-image-2", "entries": []}
    for rep in range(1, REPS + 1):
        cell = f"H-G2-OUT-GREEN-r{rep}"
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
