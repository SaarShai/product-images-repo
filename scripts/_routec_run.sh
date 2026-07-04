#!/usr/bin/env bash
# Route C helper: run ONE geom_adherence_test row with retry-on-no-image.
# Does NOT edit geom_adherence_test.py — only wraps it.
# Usage: _routec_run.sh <id> <model openai|nanobanana> <map.png> <prompt.md> <outdir>
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
ID="$1"; MODEL="$2"; MAP="$3"; PROMPT="$4"; OUTDIR="$5"
SVG="tasks/space-np01-front-bottom-02/source/template.svg"
R1="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_17_34 PM.png"
R2="tasks/space-np01-front-bottom-02/refs/ChatGPT Image Jun 9, 2026, 11_19_45 PM.png"
EXP="$OUTDIR/$ID"
for attempt in 1 2 3; do
  echo ">>> [$ID] attempt $attempt (model=$MODEL)"
  python3 scripts/geom_adherence_test.py --id "$ID" --model "$MODEL" \
    --map "$MAP" --prompt "$PROMPT" --refs "$R1" "$R2" \
    --svg "$SVG" --outdir "$OUTDIR" --timeout 300
  if [ -f "$EXP/raw.png" ]; then
    echo ">>> [$ID] raw.png present after attempt $attempt"
    break
  fi
  echo ">>> [$ID] NO raw.png after attempt $attempt; retrying"
done
[ -f "$EXP/raw.png" ] || { echo ">>> [$ID] GIVE UP no image after 3 attempts"; exit 2; }
