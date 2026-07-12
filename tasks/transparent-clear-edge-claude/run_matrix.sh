#!/usr/bin/env bash
# run_matrix.sh — 5-arm x 2-run prompt matrix via subgen.py (openai provider).
# Own pgroup via setsid; skip-if-exists; parallelism 3.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
REF='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_20_05 AM.png'
OUT='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/claude-prompt-matrix'
PDIR='tasks/transparent-clear-edge-claude/prompts'
LOG='tasks/transparent-clear-edge-claude/run_matrix.log'
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
  "M1-minimal-colorhold 1" "M2-sticker-framing 1" "M3-screenprint-framing 1" \
  "M4-styleguard-full 1" "M5-chroma-green 1" \
  "M1-minimal-colorhold 2" "M2-sticker-framing 2" "M3-screenprint-framing 2" \
  "M4-styleguard-full 2" "M5-chroma-green 2" \
| xargs -P 3 -L 1 bash -c 'job "$@"' _
echo "MATRIX COMPLETE $(date +%T)" >> "$LOG"
