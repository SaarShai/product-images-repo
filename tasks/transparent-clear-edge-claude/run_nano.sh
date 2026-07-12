#!/usr/bin/env bash
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
REF='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_20_05 AM.png'
OUT='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/claude-prompt-matrix'
PDIR='tasks/transparent-clear-edge-claude/prompts'
LOG='tasks/transparent-clear-edge-claude/run_nano.log'
: > "$LOG"
for arm in M1-minimal-colorhold M4-styleguard-full; do
  out="$OUT/${arm}-nano.png"
  [ -s "$out" ] && continue
  echo "START nano $arm $(date +%T)" >> "$LOG"
  python3 scripts/subgen.py --provider nano --prompt-file "$PDIR/full-${arm}.txt" -i "$REF" --out "$out" --timeout 420 --retries 2 >> "$LOG" 2>&1
  [ -s "$out" ] && echo "DONE nano $arm $(date +%T)" >> "$LOG" || echo "FAIL nano $arm $(date +%T)" >> "$LOG"
done
echo "NANO COMPLETE" >> "$LOG"
