#!/bin/bash
set -u; cd "/Users/za/Documents/product images repo" || exit 1
D=tasks/whole-panel-build/B4-princess-window; PY=~/ComfyUI/venv/bin/python
G=$D/guide-bleed.png; W=$D/window-cut.png; S=$D/style-ref.png; P=$D/princess01-ref.png
g(){ echo "=== $1 ==="; "$PY" scripts/subgen.py --provider openai --prompt-file "$2" --out $D/sub/$1.png "${@:3}" --timeout 520 --retries 2 || echo "FAIL $1"; }
g o1-bleed      $D/prompt-W-bleed.md          -i $G $W $S $P
g o2-elegant    $D/prompt-W-bleed-elegant.md  -i $G $W $S $P
g o3-styleonly  $D/prompt-W-bleed.md          -i $G $W $S
g o4-elegant2   $D/prompt-W-bleed-elegant.md  -i $G $W $S $P
echo O1_DONE
