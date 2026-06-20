#!/bin/bash
# Improved method: model paints the window INTO the opening (window-high), + variance re-runs. $1=provider
set -u
cd "/Users/za/Documents/product images repo" || exit 1
D=tasks/whole-panel-build/B4-princess-window; PY=~/ComfyUI/venv/bin/python; PV="$1"
G=$D/guide-clean2.png; W=$D/window-cut.png; S=$D/style-ref.png; P=$D/princess01-ref.png
g(){ echo "=== $PV-$1 ==="; "$PY" scripts/subgen.py --provider $PV --prompt-file "$2" --out $D/sub/$PV-$1.png "${@:3}" --timeout 520 --retries 2 || echo "FAIL $1"; }
g G3winin   $D/prompt-W-winin.md     -i $G $W $S $P
g G3winin2  $D/prompt-W-winin.md     -i $G $W $S $P
g G2winhigh3 $D/prompt-W-windowhigh.md -i $G $S $P
echo "${PV}_WININ_DONE"
