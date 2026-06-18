#!/usr/bin/env bash
set -u
cd "/Users/za/Documents/product images repo"

GEN="scripts/geom_adherence_test.py"
T="tasks/space-np02-front-bottom-02"
OUT="$T/experiments-outset"
PROMPT="$T/prompts/BoN-nano-letterbox-02.md"
R1="$T/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
R2="$T/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"
BASE="$T/outputs/generated/np02-fb-02-base-outset30-1440x2560.png"
SVG="$T/source/template-outset30.svg"

for n in {1..8}; do
  id="OUTSET-A-o30-s$n"
  dir="$OUT/$id"
  if [ -f "$dir/raw.png" ]; then
    echo "[skip] $id already generated"
    continue
  fi
  echo "[gen] Starting cell $id..."
  for a in 1 2 3; do
    python3 "$GEN" --id "$id" --model nanobanana --map "$BASE" --prompt "$PROMPT" \
      --refs "$R1" "$R2" --svg "$SVG" --outdir "$OUT" --timeout 360
    if [ -f "$dir/raw.png" ]; then
      echo "[gen] Cell $id succeeded on attempt $a"
      break
    fi
    echo "[gen] Attempt $a for $id failed. Retrying..."
  done
done
echo "ALL GENERATIONS COMPLETED"
