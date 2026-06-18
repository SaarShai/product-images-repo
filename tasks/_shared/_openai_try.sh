#!/usr/bin/env bash
set -u
cd "/Users/za/Documents/product images repo"
GEN="scripts/geom_adherence_test.py"
R=(tasks/_shared/refs-v2/ref2.png tasks/_shared/refs-v2/ref4.png)
gen() { # slug base prompt svg id
  local slug="$1" base="$2" prompt="$3" svg="$4" id="$5"
  local OUT="tasks/$slug/experiments-outset" dir="tasks/$slug/experiments-outset/$5"
  if [ -f "$dir/raw.png" ]; then echo "[skip] $slug $id"; return; fi
  for a in 1 2; do
    python3 "$GEN" --id "$id" --model openai --map "$base" --prompt "$prompt" \
      --refs "${R[@]}" --svg "$svg" --outdir "$OUT" --timeout 360 >/dev/null 2>&1
    [ -f "$dir/raw.png" ] && break
  done
  echo "[done] $slug $id $([ -f "$dir/raw.png" ] && echo OK || echo FAIL)"
}
gen space-np01-back-bottom-02 tasks/space-np01-back-bottom-02/outputs/generated/base-silhouette-1440x2560.png tasks/_shared/prompts/BoN-nano-back-socket-panel.md tasks/space-np01-back-bottom-02/source/template.svg OPENAI-s1
gen space-np01-back-bottom-02 tasks/space-np01-back-bottom-02/outputs/generated/base-silhouette-1440x2560.png tasks/_shared/prompts/BoN-nano-back-socket-panel.md tasks/space-np01-back-bottom-02/source/template.svg OPENAI-s2
gen space-np02-back-bottom-02 tasks/space-np02-back-bottom-02/outputs/generated/base-outset30-1440x2560.png tasks/_shared/prompts/BoN-nano-letterbox-generic.md tasks/space-np02-back-bottom-02/source/template-outset30.svg OPENAI-s1
echo "OPENAI TRY DONE"
