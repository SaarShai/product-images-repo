#!/usr/bin/env bash
# run_round4.sh — 2 arms x 3 runs, white bg, openai provider. Tests the CORE-swap lever.
# R2a = Sol reference-authority core + minimal edge; R2b = M1 champion + density nudge.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
REF='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_20_05 AM.png'
OUT='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/claude-prompt-matrix'
PDIR='tasks/transparent-clear-edge-claude/prompts'
LOG='tasks/transparent-clear-edge-claude/run_round4.log'
mkdir -p "$OUT"
: > "$LOG"
job() {
  arm="$1"; run="$2"
  out="$OUT/${arm}-r${run}.png"
  [ -s "$out" ] && { echo "skip $arm r$run (exists)" >> "$LOG"; return 0; }
  echo "START $arm r$run $(date +%T)" >> "$LOG"
  python3 scripts/subgen.py --provider openai --prompt-file "$PDIR/full-${arm}.txt" \
    -i "$REF" --out "$out" --timeout 420 --retries 2 >> "$LOG" 2>&1
  if [ -s "$out" ]; then echo "DONE  $arm r$run $(date +%T)" >> "$LOG"; else echo "FAIL  $arm r$run $(date +%T)" >> "$LOG"; fi
}
export -f job; export OUT PDIR LOG REF
printf "%s\n" \
  "R4-deviation-authorized 1" "R4-deviation-authorized 2" "R4-deviation-authorized 3" \
| xargs -P 3 -L 1 bash -c 'job "$@"' _
echo "ROUND4 COMPLETE $(date +%T)" >> "$LOG"
