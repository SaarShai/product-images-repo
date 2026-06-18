#!/usr/bin/env bash
# SRC-only serial agy (nanobanana) driver for np01-front-bottom-01.
# Mirrors space-np01-front-bottom-02/_src_agy.sh: race-safe (ONE agy at a time), resumable.
set -u
cd "/Users/za/Documents/product images repo"

GEN="scripts/geom_adherence_test.py"
T="tasks/space-np01-front-bottom-01"
OUTDIR="$T/experiments"
SVG="$T/source/template.svg"
SRC_BASE="$T/outputs/generated/np01-fb-01-base-trueaspect-1440x2560.png"
SRC_PROMPT="$T/prompts/BoN-nano-letterbox-01.md"
STYLEREF="$T/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
STYLEREF2="$T/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"

run_cell () {  # id
  local id="$1"; local dir="$OUTDIR/$id"
  if [ -f "$dir/raw.png" ]; then echo "[skip] $id already has raw.png"; return 0; fi
  local attempt
  for attempt in 1 2 3; do
    echo "[agy] $id attempt $attempt"
    python3 "$GEN" --id "$id" --model nanobanana --map "$SRC_BASE" --prompt "$SRC_PROMPT" \
      --refs "$STYLEREF" "$STYLEREF2" --svg "$SVG" --outdir "$OUTDIR" --timeout 360
    if [ -f "$dir/raw.png" ]; then echo "[agy] $id OK"; return 0; fi
    echo "[agy] $id no image (attempt $attempt)"
  done
  echo "[agy] $id FAILED after 3 attempts"; return 1
}

for n in 1 2 3 4 5 6 7 8; do run_cell "SRC-nb-s$n"; done
echo "[agy] SRC DRIVER DONE"
