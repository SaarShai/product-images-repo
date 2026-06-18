#!/usr/bin/env bash
# Regenerate 2 square tops, v2 prompt, 8 cells each, nano, SERIAL (one agy at a time).
set -u
cd "/Users/za/Documents/product images repo"
GEN="scripts/geom_adherence_test.py"
PROMPT="tasks/_shared/prompts/BoN-nano-square-top-v2.md"
for slug in space-np01-back-top space-np02-front-top; do
  T="tasks/$slug"; OUT="$T/experiments-outset"
  cp "$PROMPT" "$T/prompts/" 2>/dev/null
  BASE="$T/outputs/generated/base-outset30-sq-1700x1620.png"
  SVG="$T/source/template-outset30.svg"
  R1="$T/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
  R2="$T/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"
  for n in 1 2 3 4 5 6 7 8; do
    id="OUTSET-A-o30-sqv2-s$n"; dir="$OUT/$id"
    [ -f "$dir/raw.png" ] && { echo "[skip] $slug $id"; continue; }
    for a in 1 2 3; do
      python3 "$GEN" --id "$id" --model nanobanana --map "$BASE" --prompt "$PROMPT" \
        --refs "$R1" "$R2" --svg "$SVG" --outdir "$OUT" --timeout 360 >/dev/null 2>&1
      [ -f "$dir/raw.png" ] && break
    done
    echo "[done] $slug $id $([ -f "$dir/raw.png" ] && echo OK || echo FAIL)"
  done
done
echo "TOPS V2 DONE"
