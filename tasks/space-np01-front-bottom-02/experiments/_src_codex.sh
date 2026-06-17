#!/usr/bin/env bash
# SRC-only serial codex (openai) driver — race-safe (ONE codex at a time), resumable, retry-on-no-image.
# Generates COLORFUL reference-matched SOURCE panels (priority #1).
set -u
cd "/Users/za/Documents/product images repo"

GEN="scripts/geom_adherence_test.py"
OUTDIR="tasks/space-np01-front-bottom-02/experiments"
SVG="tasks/space-np01-front-bottom-02/source/template.svg"
SRC_BASE="tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-base-trueaspect-1440x2560.png"
SRC_PROMPT="tasks/space-np01-front-bottom-02/prompts/BoN2-openai-letterbox.md"
STYLEREF="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
STYLEREF2="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"

run_cell () {  # id
  local id="$1"; local dir="$OUTDIR/$id"
  if [ -f "$dir/raw.png" ]; then echo "[skip] $id already has raw.png"; return 0; fi
  local attempt
  for attempt in 1 2 3; do
    echo "[codex] $id attempt $attempt"
    python3 "$GEN" --id "$id" --model openai --map "$SRC_BASE" --prompt "$SRC_PROMPT" \
      --refs "$STYLEREF" "$STYLEREF2" --svg "$SVG" --outdir "$OUTDIR" --timeout 360
    if [ -f "$dir/raw.png" ]; then echo "[codex] $id OK"; return 0; fi
    echo "[codex] $id no image (attempt $attempt)"
  done
  echo "[codex] $id FAILED after 3 attempts"; return 1
}

for n in 1 2 3 4 5 6 7 8; do run_cell "SRC-oai-s$n"; done
echo "[codex] SRC DRIVER DONE"
