#!/bin/bash
# Princess-window experiment, one provider's track (serialized). $1 = openai|nano
set -u
cd "/Users/za/Documents/product images repo" || exit 1
D=tasks/whole-panel-build/B4-princess-window; PY=~/ComfyUI/venv/bin/python; PROV="$1"
mkdir -p $D/sub
g(){ echo "=== $PROV-$1 ==="; "$PY" scripts/subgen.py --provider $PROV --prompt-file "$2" --out $D/sub/$PROV-$1.png "${@:3}" --timeout 520 --retries 2 || echo "FAIL $1"; }
# C1: door shown in guide
g C1guide  $D/prompt-W-guide.md      -i $D/guide-window.png $D/style-ref.png $D/princess01-ref.png
# C3: window as separate exact ref + plain outline guide
g C3winref $D/prompt-W-windowref.md  -i $D/guide-plain.png $D/window-cut.png $D/style-ref.png $D/princess01-ref.png
echo "${PROV}_TRACK_DONE"
