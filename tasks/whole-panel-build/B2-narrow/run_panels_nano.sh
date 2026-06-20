#!/bin/bash
# Cross-check: nano on m3 (tall slot+circle) and m4 (hexagon cutouts) — serialized (one agy at a time).
set -u
cd "/Users/za/Documents/product images repo" || exit 1
P=tasks/whole-panel-build/B2-narrow/panels; AN=tasks/whole-panel-build/anchors/space-narrow-panels-01
PR=tasks/whole-panel-build/B2-narrow/prompt-VALID.md
PY=~/ComfyUI/venv/bin/python; mkdir -p $P/sub
gen(){ echo "=== $1 (style=$3) ==="; "$PY" scripts/subgen.py --provider nano --prompt-file $PR --out $P/sub/nano-$1.png -i $P/panel-$1-geomguide.png $AN/illustration-$2.png --timeout 460 --retries 2 || echo "FAIL $1"; }
gen m3 6 "paint-6"
gen m4 9 "paint-9"
echo NANO_PANELS_DONE
