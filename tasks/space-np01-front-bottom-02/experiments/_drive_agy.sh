#!/usr/bin/env bash
# Serial agy (nanobanana) driver — race-safe (only ONE agy at a time), resumable.
# Does NOT edit any generator script. Just calls scripts/geom_adherence_test.py per cell.
set -u
cd "/Users/za/Documents/product images repo"

GEN="scripts/geom_adherence_test.py"
OUTDIR="tasks/space-np01-front-bottom-02/experiments"
SVG="tasks/space-np01-front-bottom-02/source/template.svg"

EXACT_DREAM="tasks/space-np01-front-bottom-02/experiments/DREAM1/exact.png"
EXACT_CN="tasks/space-np01-front-bottom-02/experiments/CN-style-exact/raw.png"
SRC_BASE="tasks/space-np01-front-bottom-02/outputs/generated/np01-fb-02-base-trueaspect-1440x2560.png"

RIP_V1="tasks/space-np01-front-bottom-02/prompts/RIP-v1.md"
RIP_V3="tasks/space-np01-front-bottom-02/prompts/RIP-v3.md"
SRC_PROMPT="tasks/space-np01-front-bottom-02/prompts/BoN2-nano-letterbox.md"

STYLEREF="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
STYLEREF2="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"

run_cell () {  # id  map  prompt  "refs..."
  local id="$1"; local map="$2"; local prompt="$3"; shift 3
  local dir="$OUTDIR/$id"
  if [ -f "$dir/raw.png" ]; then echo "[skip] $id already has raw.png"; return 0; fi
  local attempt
  for attempt in 1 2 3; do
    echo "[agy] $id attempt $attempt -> map=$(basename "$map") prompt=$(basename "$prompt")"
    python3 "$GEN" --id "$id" --model nanobanana --map "$map" --prompt "$prompt" \
      --refs "$@" --svg "$SVG" --outdir "$OUTDIR" --timeout 360
    if [ -f "$dir/raw.png" ]; then echo "[agy] $id OK"; return 0; fi
    echo "[agy] $id no image (attempt $attempt)"
  done
  echo "[agy] $id FAILED after 3 attempts"; return 1
}

# ---- SUB-ROUTE C-sub: restyle-in-place (RESTYLE-nb-*) : ~6 cells (s1 already done) ----
run_cell "RESTYLE-nb-v3-s2" "$EXACT_DREAM" "$RIP_V3" "$STYLEREF"
run_cell "RESTYLE-nb-v3-s3" "$EXACT_CN"    "$RIP_V3" "$STYLEREF"
run_cell "RESTYLE-nb-v1-s1" "$EXACT_DREAM" "$RIP_V1" "$STYLEREF"
run_cell "RESTYLE-nb-v1-s2" "$EXACT_CN"    "$RIP_V1" "$STYLEREF"
run_cell "RESTYLE-nb-v1-s3" "$EXACT_DREAM" "$RIP_V1" "$STYLEREF"

# ---- SUB-ROUTE D: gorgeous SOURCE panels (SRC-nb-sN) : 6 cells ----
run_cell "SRC-nb-s1" "$SRC_BASE" "$SRC_PROMPT" "$STYLEREF" "$STYLEREF2"
run_cell "SRC-nb-s2" "$SRC_BASE" "$SRC_PROMPT" "$STYLEREF" "$STYLEREF2"
run_cell "SRC-nb-s3" "$SRC_BASE" "$SRC_PROMPT" "$STYLEREF" "$STYLEREF2"
run_cell "SRC-nb-s4" "$SRC_BASE" "$SRC_PROMPT" "$STYLEREF" "$STYLEREF2"
run_cell "SRC-nb-s5" "$SRC_BASE" "$SRC_PROMPT" "$STYLEREF" "$STYLEREF2"
run_cell "SRC-nb-s6" "$SRC_BASE" "$SRC_PROMPT" "$STYLEREF" "$STYLEREF2"

echo "[agy] DRIVER DONE"
