#!/usr/bin/env bash
# More-outset sweep (Way A), np01-front-bottom-01. 18/24/30 pt, 2 cells each.
set -u
cd "/Users/za/Documents/product images repo"
GEN="scripts/geom_adherence_test.py"
T="tasks/space-np01-front-bottom-01"
OUT="$T/experiments-outset"
PROMPT="$T/prompts/BoN-nano-letterbox-01.md"
R1="$T/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
R2="$T/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"

cell () {  # id base svg
  local id="$1" map="$2" svg="$3" dir="$OUT/$1"
  if [ -f "$dir/raw.png" ]; then echo "[skip] $id"; return 0; fi
  for a in 1 2 3; do
    echo "[gen] $id attempt $a"
    python3 "$GEN" --id "$id" --model nanobanana --map "$map" --prompt "$PROMPT" \
      --refs "$R1" "$R2" --svg "$svg" --outdir "$OUT" --timeout 360
    [ -f "$dir/raw.png" ] && { echo "[gen] $id OK"; return 0; }
  done
  echo "[gen] $id FAILED"; return 1
}

for o in 18 24 30; do
  for n in 1 2; do
    cell "OUTSET-A-o${o}-s$n" \
      "$T/outputs/generated/np01-fb-01-base-outset${o}-1440x2560.png" \
      "$T/source/template-outset${o}.svg"
  done
done
echo "MORE OUTSET DONE"
