#!/usr/bin/env bash
set -u
cd "/Users/za/Documents/product images repo"
GEN="scripts/geom_adherence_test.py"
R=(tasks/_shared/refs-v2/ref2.png tasks/_shared/refs-v2/ref4.png)
run() {
  local slug="$1"; local base="$2"; local prompt="$3"; local svg="$4"
  local OUT="tasks/$slug/experiments-outset"
  local n a id dir
  for n in 1 2 3 4 5 6; do
    id="REFV2-s$n"; dir="$OUT/$id"
    if [ -f "$dir/raw.png" ]; then echo "[skip] $slug $id"; continue; fi
    for a in 1 2 3; do
      python3 "$GEN" --id "$id" --model nanobanana --map "$base" --prompt "$prompt" \
        --refs "${R[@]}" --svg "$svg" --outdir "$OUT" --timeout 360 >/dev/null 2>&1
      if [ -f "$dir/raw.png" ]; then break; fi
    done
    echo "[done] $slug $id $([ -f "$dir/raw.png" ] && echo OK || echo FAIL)"
  done
}
run space-np01-back-bottom-02 tasks/space-np01-back-bottom-02/outputs/generated/base-silhouette-1440x2560.png tasks/_shared/prompts/BoN-nano-back-socket-panel.md tasks/space-np01-back-bottom-02/source/template.svg
run space-np02-front-bottom-01 tasks/space-np02-front-bottom-01/outputs/generated/base-silhouette-1440x2560.png tasks/_shared/prompts/BoN-nano-plain-panel.md tasks/space-np02-front-bottom-01/source/template.svg
run space-np02-back-bottom-02 tasks/space-np02-back-bottom-02/outputs/generated/base-outset30-1440x2560.png tasks/_shared/prompts/BoN-nano-letterbox-generic.md tasks/space-np02-back-bottom-02/source/template-outset30.svg
echo "REFSV2 REGEN DONE"
