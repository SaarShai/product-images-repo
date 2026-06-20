#!/bin/bash
set -u; cd "/Users/za/Documents/product images repo" || exit 1
D=tasks/whole-panel-build/B4-princess-window; PY=~/ComfyUI/venv/bin/python
G=$D/guide-bleed.png; W=$D/window-cut.png; S=$D/style-ref.png; P=$D/princess01-ref.png
g(){ echo "=== $1 ==="; "$PY" scripts/subgen.py --provider nano --prompt-file "$2" --out $D/sub/$1.png "${@:3}" --timeout 520 --retries 2 || echo "FAIL $1"; }
g n1-elegant   $D/prompt-W-bleed-elegant.md -i $G $W $S $P
g n2-polishG4  $D/prompt-W-polish.md        -i $D/sub/openai-G4bleed.png $S
echo N_DONE
