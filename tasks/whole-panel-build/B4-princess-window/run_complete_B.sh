#!/bin/bash
set -u; cd "/Users/za/Documents/product images repo" || exit 1
D=tasks/whole-panel-build/B4-princess-window; PY=~/ComfyUI/venv/bin/python
Gc=$D/guide-clean2.png; W=$D/window-cut.png; S=$D/style-ref.png; P=$D/princess01-ref.png
g(){ echo "=== $1 ==="; "$PY" scripts/subgen.py --provider openai --prompt-file $D/prompt-W-complete.md --out $D/sub/$1.png "${@:2}" --timeout 520 --retries 2 || echo "FAIL $1"; }
g cB1-clean-styleP   -i $Gc $W $S $P
g cB2-clean-Pstyle   -i $Gc $W $P $S
echo B_DONE
