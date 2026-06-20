#!/bin/bash
# Serialized openai/codex matrix (separate binary from agy, runs in parallel with the agy track).
set -u
cd "/Users/za/Documents/product images repo" || exit 1
D=tasks/whole-panel-build/B2-narrow; SC=$D/stylecrops
PY=~/ComfyUI/venv/bin/python
T=tasks/whole-panel-build/anchors/space-narrow-panels-01/illustration-10.png
G=$D/panel3-geomguide.png
run(){ echo "=== $1 ==="; "$PY" scripts/subgen.py --provider openai --prompt-file "$2" --out "$3" "${@:4}" --timeout 460 --retries 2 || echo "FAILED $1"; }
run GS2  $D/prompt-GS.md  $D/sub/openai-GS2.png  -i $G $T $SC/gauge_pills.png $SC/toggles_sliders.png
run noC  $D/prompt-GS.md  $D/sub/openai-noC.png  -i $G $T
run R    $D/prompt-R.md   $D/sub/openai-R.png    -i $G $D/style1/exact.png $T $SC/gauge_pills.png $SC/toggles_sliders.png
echo "CODEX_TRACK_DONE"
