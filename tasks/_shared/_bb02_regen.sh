#!/usr/bin/env bash
# np01-back-bottom-02 regen: corrected silhouette base + back-socket prompt. 6 cells, nano, serial.
set -u
cd "/Users/za/Documents/product images repo"
# wait for tops v2 to finish first (one agy at a time)
while ! grep -q "TOPS V2 DONE" tasks/_shared/_tops_v2.log 2>/dev/null; do sleep 10; done
GEN="scripts/geom_adherence_test.py"
T="tasks/space-np01-back-bottom-02"; OUT="$T/experiments-outset"
BASE="$T/outputs/generated/base-silhouette-1440x2560.png"
SVG="$T/source/template.svg"
PROMPT="tasks/_shared/prompts/BoN-nano-back-socket-panel.md"
cp "$PROMPT" "$T/prompts/" 2>/dev/null
R1="$T/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
R2="$T/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"
for n in 1 2 3 4 5 6; do
  id="SOCKETFIX-s$n"; dir="$OUT/$id"
  [ -f "$dir/raw.png" ] && { echo "[skip] $id"; continue; }
  for a in 1 2 3; do
    python3 "$GEN" --id "$id" --model nanobanana --map "$BASE" --prompt "$PROMPT" \
      --refs "$R1" "$R2" --svg "$SVG" --outdir "$OUT" --timeout 360 >/dev/null 2>&1
    [ -f "$dir/raw.png" ] && break
  done
  echo "[done] $id $([ -f "$dir/raw.png" ] && echo OK || echo FAIL)"
done
echo "BB02 SOCKETFIX DONE"
