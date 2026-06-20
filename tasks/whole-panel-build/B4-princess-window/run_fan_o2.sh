#!/bin/bash
set -u; cd "/Users/za/Documents/product images repo" || exit 1
D=tasks/whole-panel-build/B4-princess-window; PY=~/ComfyUI/venv/bin/python; S=$D/style-ref.png
g(){ echo "=== $1 ==="; "$PY" scripts/subgen.py --provider openai --prompt-file "$2" --out $D/sub/$1.png "${@:3}" --timeout 520 --retries 2 || echo "FAIL $1"; }
g o5-polishG4   $D/prompt-W-polish.md    -i $D/sub/openai-G4bleed.png $S
g o6-editG3w2   $D/prompt-W-fixedges.md  -i $D/sub/openai-G3winin2.png $S
g o7-polishAed  $D/prompt-W-polish.md    -i $D/sub/openai-Aedit.png $S
echo O2_DONE
