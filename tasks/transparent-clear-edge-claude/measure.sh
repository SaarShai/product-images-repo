#!/usr/bin/env bash
# measure.sh — per-candidate gate pass: aura_gate + keyer (white or chroma) + thumbs.
set -u
cd "$(cd "$(dirname "$0")/../.." && pwd)"
CAND='/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/double Marine Bed Wrapper/images/Images/candidates/claude-prompt-matrix'
TH="$CAND/thumbs"; mkdir -p "$TH"
for f in "$CAND"/M*-r*.png; do
  [ -e "$f" ] || continue
  b=$(basename "$f" .png)
  case "$b" in *rgba*|*check*) continue;; esac
  # aura gate (nonwhite mode for raw on solid bg)
  if [ ! -s "$CAND/$b.aura.json" ]; then
    python3 scripts/aura_gate.py "$f" --nonwhite "$f" --json "$CAND/$b.aura.json" --overlay-dir "$TH" 2>/dev/null | tail -1
  fi
  # keyer
  if [ ! -s "$CAND/$b-rgba.png" ]; then
    case "$b" in
      M5-*) python3 scripts/chroma_key.py key "$f" "$CAND/$b-rgba.png" 2>&1 | tail -1 ;;
      *)    python3 scripts/white_key.py --image "$f" --out "$CAND/$b-rgba.png" 2>&1 | tail -1 ;;
    esac
  fi
  # magenta-composite check of the keyed rgba + thumbnails
  python3 - "$f" "$CAND/$b-rgba.png" "$TH/$b.jpg" "$TH/$b-keycheck.jpg" <<'PY'
import sys
from PIL import Image
raw, rgba_p, thumb, keycheck = sys.argv[1:5]
im = Image.open(raw); im.thumbnail((380, 950)); im.convert("RGB").save(thumb, quality=85)
try:
    r = Image.open(rgba_p).convert("RGBA")
    bg = Image.new("RGBA", r.size, (255, 0, 255, 255))
    comp = Image.alpha_composite(bg, r); comp.thumbnail((380, 950))
    comp.convert("RGB").save(keycheck, quality=85)
except FileNotFoundError:
    pass
PY
done
echo "measured: $(ls "$CAND"/*.aura.json 2>/dev/null | wc -l | tr -d ' ') candidates"
