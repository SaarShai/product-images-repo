#!/usr/bin/env bash
# Outset keep-clear test, np01-front-bottom-01. Two ways, 3 cells each.
# A = adapt SVG (outset base image is the contract). B = prompt-only outset instruction.
set -u
cd "/Users/za/Documents/product images repo"
GEN="scripts/geom_adherence_test.py"
T="tasks/space-np01-front-bottom-01"
OUT="$T/experiments-outset"
SVG="$T/source/template.svg"
SVG_OUT="$T/source/template-outset12.svg"
BASE="$T/outputs/generated/np01-fb-01-base-trueaspect-1440x2560.png"
BASE_OUT="$T/outputs/generated/np01-fb-01-base-outset12-1440x2560.png"
PROMPT="$T/prompts/BoN-nano-letterbox-01.md"
PROMPT_OUT="$T/prompts/BoN-nano-letterbox-01-outset.md"
R1="$T/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
R2="$T/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"

cell () {  # id map prompt svg
  local id="$1" map="$2" prompt="$3" svg="$4" dir="$OUT/$1"
  if [ -f "$dir/raw.png" ]; then echo "[skip] $id"; return 0; fi
  for a in 1 2 3; do
    echo "[gen] $id attempt $a"
    python3 "$GEN" --id "$id" --model nanobanana --map "$map" --prompt "$prompt" \
      --refs "$R1" "$R2" --svg "$svg" --outdir "$OUT" --timeout 360
    [ -f "$dir/raw.png" ] && { echo "[gen] $id OK"; return 0; }
  done
  echo "[gen] $id FAILED"; return 1
}

for n in 1 2 3; do cell "OUTSET-A-svg-s$n" "$BASE_OUT" "$PROMPT"     "$SVG_OUT"; done
for n in 1 2 3; do cell "OUTSET-B-prompt-s$n" "$BASE" "$PROMPT_OUT" "$SVG"; done
echo "OUTSET TEST DONE"
