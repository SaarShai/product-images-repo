#!/usr/bin/env bash
set -u
cd "/Users/za/Documents/product images repo"
GEN="scripts/geom_adherence_test.py"
T="tasks/space-np01-front-bottom-01"; OUT="$T/experiments-outset"
PROMPT="$T/prompts/BoN-nano-letterbox-01.md"
R1="$T/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
R2="$T/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"
BASE="$T/outputs/generated/np01-fb-01-base-outset30-1440x2560.png"
SVG="$T/source/template-outset30.svg"
for n in 3 4 5 6; do
  id="OUTSET-A-o30-s$n"; dir="$OUT/$id"
  [ -f "$dir/raw.png" ] && { echo "[skip] $id"; continue; }
  for a in 1 2 3; do
    python3 "$GEN" --id "$id" --model nanobanana --map "$BASE" --prompt "$PROMPT" \
      --refs "$R1" "$R2" --svg "$SVG" --outdir "$OUT" --timeout 360
    [ -f "$dir/raw.png" ] && break
  done
done
echo "O30 MORE DONE"
