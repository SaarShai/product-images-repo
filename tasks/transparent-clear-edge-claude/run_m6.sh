#!/usr/bin/env bash
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
REF='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/ChatGPT Image Jul 7, 2026, 11_20_05 AM.png'
OUT='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/claude-prompt-matrix'
LOG='tasks/transparent-clear-edge-claude/run_m6.log'; : > "$LOG"
for r in 1 2; do
  out="$OUT/M6-selective-contour-r${r}.png"
  [ -s "$out" ] && continue
  ( python3 scripts/subgen.py --provider openai --prompt-file tasks/transparent-clear-edge-claude/prompts/full-M6-selective-contour.txt -i "$REF" --out "$out" --timeout 420 --retries 2 >> "$LOG" 2>&1; echo "EXIT $r: $([ -s "$out" ] && echo DONE || echo FAIL)" >> "$LOG" ) &
done
wait; echo "M6 COMPLETE" >> "$LOG"
