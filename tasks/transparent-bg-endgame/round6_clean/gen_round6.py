#!/usr/bin/env python3
"""Round-6: R24/R25 — no isolated thin-filament fans, no pure-green art.

Round-5 verdict: good except thin-branch corals (artifacts at branch
intersections) and a few stray edge pixels. Root cause of both: hair-thin
strand fans trap key color at crossings, and bright pure-green art forces
conservative keying. Fix at the SOURCE (prompt), so the purge can run
unconditionally aggressive (--no-green-art).
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
sys.path.insert(0, str(REPO / "tasks" / "transparent-bg-endgame" / "round5_med"))
from _falcommon import load_openai_key  # noqa: E402
from gen_round3 import EXCLUSIONS_BLOCK, HARD_EDGE_BLOCK, RICH_STYLE_BLOCK  # noqa: E402
from gen_round4 import BG_SPECS, bg_flatness, extract_b64, key_bg_block, poll, submit  # noqa: E402
from gen_round5 import MEDIUM_CONTOUR_BLOCK  # noqa: E402

REPS = 2

SUBJECT_BLOCK_V2 = (
    "[SUBJECT H]\n"
    "Create a single watercolor coral cluster with closed ink contours. "
    "The cluster must contain ALL of these visible elements: one seaweed "
    "sprig in muted OLIVE or SAGE green (never bright pure green), pale "
    "tinted off-white barnacle details, several slender coral branches, and "
    "intentional negative-space gaps between branches. Nothing touches the "
    "canvas edges; keep a clear margin on all four sides."
)

NO_FILAMENT_BLOCK = (
    "[STRUCTURE - NO LOOSE FILAMENTS]\n"
    "Absolutely no feather-duster fans, hair-thin tentacle sprays, or "
    "clusters of individual wispy strands radiating over open background. "
    "Every branch, frond, and antenna is a SOLID painted shape at least as "
    "wide as a fine felt-tip line, with its own closed contour, and branch "
    "junctions merge smoothly into solid painted joints - no lattice of "
    "crossing hairlines with background showing through the crossings. "
    "Delicacy comes from interior brushwork and color, not from strand "
    "thinness."
)

NO_GREEN_ART_BLOCK = (
    "[PALETTE CONSTRAINT - NO PURE GREEN]\n"
    "Because the background is pure chroma green, NO part of the subject may "
    "use bright, pure, or saturated green. Any plant or seaweed element uses "
    "muted olive, sage, sea-teal, or yellow-green earth tones clearly "
    "distinct from the background green. No green highlights, no green "
    "reflections, no grass-green accents anywhere in the artwork."
)


def build_prompt(bg_desc: str) -> str:
    return "\n\n".join(
        [
            SUBJECT_BLOCK_V2,
            RICH_STYLE_BLOCK,
            MEDIUM_CONTOUR_BLOCK,
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
    (PROMPT_DIR / "clean_GREEN.txt").write_text(prompt + "\n")
    manifest = {"experiment": "round6_clean", "model": "gpt-image-2", "entries": []}
    for rep in range(1, REPS + 1):
        cell = f"H-G2-CLEAN-GREEN-r{rep}"
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
