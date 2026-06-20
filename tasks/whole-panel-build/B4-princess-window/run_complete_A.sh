#!/bin/bash
set -u; cd "/Users/za/Documents/product images repo" || exit 1
D=tasks/whole-panel-build/B4-princess-window; PY=~/ComfyUI/venv/bin/python
Gb=$D/guide-bleed.png; W=$D/window-cut.png; S=$D/style-ref.png; P=$D/princess01-ref.png
g(){ echo "=== $1 ==="; "$PY" scripts/subgen.py --provider openai --prompt-file $D/prompt-W-complete.md --out $D/sub/$1.png "${@:2}" --timeout 520 --retries 2 || echo "FAIL $1"; }
g cA1-bleed-styleP   -i $Gb $W $S $P
g cA2-bleed-Pstyle   -i $Gb $W $P $S
echo A_DONE
