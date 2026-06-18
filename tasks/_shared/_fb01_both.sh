#!/usr/bin/env bash
set -u
cd "/Users/za/Documents/product images repo"
GEN="scripts/geom_adherence_test.py"
T="tasks/space-np02-front-bottom-01"; OUT="$T/experiments-outset"
BASE="$T/outputs/generated/base-silhouette-v2-1440x2560.png"
SVG="$T/source/template.svg"
PROMPT="tasks/_shared/prompts/BoN-nano-plain-panel.md"
R=(tasks/_shared/refs-v2/ref1.png tasks/_shared/refs-v2/ref2.png tasks/_shared/refs-v2/ref3.png tasks/_shared/refs-v2/ref4.png tasks/_shared/refs-v2/ref5.png)
cell() { # model id
  local model="$1" id="$2" dir="$OUT/$2"
  if [ -f "$dir/raw.png" ]; then echo "[skip] $id"; return; fi
  for a in 1 2 3; do
    python3 "$GEN" --id "$id" --model "$model" --map "$BASE" --prompt "$PROMPT" \
      --refs "${R[@]}" --svg "$SVG" --outdir "$OUT" --timeout 360 >/dev/null 2>&1
    [ -f "$dir/raw.png" ] && break
  done
  echo "[done] $id $([ -f "$dir/raw.png" ] && echo OK || echo FAIL)"
}
for n in 1 2 3 4 5 6; do cell nanobanana "FB01-NANO-s$n"; done
for n in 1 2 3 4; do cell openai "FB01-OPENAI-s$n"; done
echo "FB01 BOTH DONE"
