#!/bin/bash
# Full-bleed window-in-opening (fix sharp edges + arch/background). $1=provider, runs 2 attempts.
set -u
cd "/Users/za/Documents/product images repo" || exit 1
D=tasks/whole-panel-build/B4-princess-window; PY=~/ComfyUI/venv/bin/python; PV="$1"
G=$D/guide-bleed.png; W=$D/window-cut.png; S=$D/style-ref.png; P=$D/princess01-ref.png
g(){ echo "=== $PV-$1 ==="; "$PY" scripts/subgen.py --provider $PV --prompt-file $D/prompt-W-bleed.md --out $D/sub/$PV-$1.png -i $G $W $S $P --timeout 520 --retries 2 || echo "FAIL $1"; }
g G4bleed
g G4bleed2
echo "${PV}_BLEED_DONE"
