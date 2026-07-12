#!/usr/bin/env bash
# run_heldout.sh — held-out generalization test: gen a tree REFERENCE (no constraints),
# then apply the R4 winning prompt structure to it x3.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
OUT='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/claude-prompt-matrix'
PDIR='tasks/transparent-clear-edge-claude/prompts'
LOG='tasks/transparent-clear-edge-claude/run_heldout.log'
: > "$LOG"
REFOUT="$OUT/H1-tree-reference.png"
if [ ! -s "$REFOUT" ]; then
  echo "START reference $(date +%T)" >> "$LOG"
  python3 scripts/subgen.py --provider openai \
    --prompt 'A tall watercolor illustration of a single friendly autumn tree for a children'"'"'s picture book: broad trunk, layered foliage in warm orange, amber, and sage washes, a few falling leaves, soft ambient light, translucent pigment with gentle granulation, on a plain white background. Natural branch and twig detail is welcome.' \
    --out "$REFOUT" --timeout 420 --retries 2 >> "$LOG" 2>&1
  [ -s "$REFOUT" ] && echo "DONE reference $(date +%T)" >> "$LOG" || { echo "FAIL reference" >> "$LOG"; exit 1; }
fi
job() {
  run="$1"; out="$OUT/H1-tree-heldout-r${run}.png"
  [ -s "$out" ] && return 0
  echo "START H1 r$run $(date +%T)" >> "$LOG"
  python3 scripts/subgen.py --provider openai --prompt-file "$PDIR/full-H1-tree-heldout.txt" \
    -i "$REFOUT" --out "$out" --timeout 420 --retries 2 >> "$LOG" 2>&1
  if [ -s "$out" ]; then echo "DONE  H1 r$run $(date +%T)" >> "$LOG"; else echo "FAIL  H1 r$run $(date +%T)" >> "$LOG"; fi
}
export -f job; export OUT PDIR LOG
printf "%s\n" 1 2 3 | xargs -P 3 -L 1 bash -c 'job "$@"' _
echo "HELDOUT COMPLETE $(date +%T)" >> "$LOG"
