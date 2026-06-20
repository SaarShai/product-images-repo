#!/bin/bash
# Valid-flow robustness test on panels m2-m5 via openai (best generalizer).
# Each: geometry guide of panel mN + a HELD-OUT different panel's painting as style.
set -u
cd "/Users/za/Documents/product images repo" || exit 1
P=tasks/whole-panel-build/B2-narrow/panels; AN=tasks/whole-panel-build/anchors/space-narrow-panels-01
PR=tasks/whole-panel-build/B2-narrow/prompt-VALID.md
PY=~/ComfyUI/venv/bin/python; mkdir -p $P/sub
gen(){ echo "=== $1 (style=$3) ==="; "$PY" scripts/subgen.py --provider openai --prompt-file $PR --out $P/sub/openai-$1.png -i $P/panel-$1-geomguide.png $AN/illustration-$2.png --timeout 460 --retries 2 || echo "FAIL $1"; }
gen m2 7 "paint-7"
gen m3 6 "paint-6"
gen m4 9 "paint-9"
gen m5 8 "paint-8"
echo OPENAI_PANELS_DONE
