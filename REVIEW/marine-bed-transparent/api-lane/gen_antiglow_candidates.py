#!/usr/bin/env python3
"""gen_antiglow_candidates.py — 2 new API-lane candidates with an
anti-aura-augmented prompt, chatgpt-image-latest only.

Same call pattern as gen_api_candidates.py (OpenAI images/edits,
background=transparent, quality=high, size=1024x1536), but using
PROMPT-coral-tower-transparent-antiglow.md, which adds (on top of the
original prompt): the repo's banked edge-hygiene block verbatim from
skills/transparent-product-image-gen/SKILL.md, plus an explicit anti-aura/
anti-glow clause, to try to suppress the painted-glow defect measured by
scripts/aura_gate.py.

Saves api-chatgpt-image-latest-antiglow{1,2}.png into this folder and
appends per-call entries to gates.json (same schema as gen_api_candidates.py
uses, `entries` list) without touching the existing 4 entries.

Usage:
  .venv-bg/bin/python3 gen_antiglow_candidates.py
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gen_api_candidates import (  # noqa: E402
    OUT_DIR,
    QUALITY,
    SIZE,
    analyze,
    call_edit,
    call_generate,
    save_from_response,
)

sys.path.insert(0, "/Users/za/Documents/product images repo/scripts")
from _falcommon import load_openai_key  # noqa: E402

import json  # noqa: E402
import requests  # noqa: E402

MODEL = "chatgpt-image-latest"
CALLS = 2
PROMPT_PATH = OUT_DIR / "PROMPT-coral-tower-transparent-antiglow.md"


def main():
    key = load_openai_key()
    prompt = PROMPT_PATH.read_text()
    gates_path = OUT_DIR / "gates.json"
    gates = json.loads(gates_path.read_text())

    for seed_idx in range(1, CALLS + 1):
        out_path = OUT_DIR / f"api-{MODEL.replace('.', '_')}-antiglow{seed_idx}.png"
        entry = {"model": MODEL, "variant": "antiglow", "seed_idx": seed_idx, "path": str(out_path)}
        t0 = time.time()
        try:
            r = call_edit(MODEL, key, prompt)
            entry["endpoint_tried"] = ["edits"]
            if r.status_code != 200:
                entry["edits_error"] = f"HTTP {r.status_code}: {r.text[:1000]}"
                print(f"[{MODEL} antiglow{seed_idx}] edits failed: {entry['edits_error']}", file=sys.stderr)
                print(f"[{MODEL} antiglow{seed_idx}] falling back to generations", file=sys.stderr)
                r2 = call_generate(MODEL, key, prompt)
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
        print(f"[{MODEL} antiglow{seed_idx}] done in {entry['duration_s']}s -> "
              f"{'OK' if out_path.exists() else 'FAILED'}")
        gates["entries"].append(entry)
        gates_path.write_text(json.dumps(gates, indent=2))

    print("DONE. antiglow candidates + gates.json updated.")


if __name__ == "__main__":
    main()
