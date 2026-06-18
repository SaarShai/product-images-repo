#!/usr/bin/env bash
set -u
cd "/Users/za/Documents/product images repo"
GEN="scripts/geom_adherence_test.py"
T="tasks/space-np01-back-bottom-02"; OUT="$T/experiments-outset"
BASE="$T/outputs/generated/base-silhouette-v2-1440x2560.png"
SVG="$T/source/template.svg"
PROMPT="tasks/_shared/prompts/BoN-nano-back-socket-panel.md"
R=(tasks/_shared/refs-v2/ref2.png tasks/_shared/refs-v2/ref4.png)
for n in 1 2 3 4 5 6; do
  id="NANOV2-s$n"; dir="$OUT/$id"
  if [ -f "$dir/raw.png" ]; then echo "[skip] $id"; continue; fi
  for a in 1 2 3; do
    python3 "$GEN" --id "$id" --model nanobanana --map "$BASE" --prompt "$PROMPT" \
      --refs "${R[@]}" --svg "$SVG" --outdir "$OUT" --timeout 360 >/dev/null 2>&1
    [ -f "$dir/raw.png" ] && break
  done
  echo "[done] $id $([ -f "$dir/raw.png" ] && echo OK || echo FAIL)"
done
echo "BB02 NANO V2 DONE"
