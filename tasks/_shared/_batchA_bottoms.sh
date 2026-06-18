#!/usr/bin/env bash
# Batch A — 5 tall-narrow bottom panels, official outset+keep-raw method. 6 cells each, nano.
set -u
cd "/Users/za/Documents/product images repo"
GEN="scripts/geom_adherence_test.py"
PROMPT="tasks/_shared/prompts/BoN-nano-letterbox-generic.md"
slugs=(space-np01-back-bottom-01 space-np01-back-bottom-02 space-np02-back-bottom-01 space-np02-back-bottom-02 space-np02-front-bottom-01)
for slug in "${slugs[@]}"; do
  T="tasks/$slug"; OUT="$T/experiments-outset"
  BASE="$T/outputs/generated/base-outset30-1440x2560.png"
  SVG="$T/source/template-outset30.svg"
  R1="$T/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
  R2="$T/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"
  for n in 1 2 3 4 5 6; do
    id="OUTSET-A-o30-s$n"; dir="$OUT/$id"
    [ -f "$dir/raw.png" ] && { echo "[skip] $slug $id"; continue; }
    for a in 1 2 3; do
      python3 "$GEN" --id "$id" --model nanobanana --map "$BASE" --prompt "$PROMPT" \
        --refs "$R1" "$R2" --svg "$SVG" --outdir "$OUT" --timeout 360 >/dev/null 2>&1
      [ -f "$dir/raw.png" ] && break
    done
    echo "[done] $slug $id $([ -f "$dir/raw.png" ] && echo OK || echo FAIL)"
  done
done
echo "BATCH A DONE"
