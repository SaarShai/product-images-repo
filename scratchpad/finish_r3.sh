#!/bin/zsh
set -e
cd "/Users/za/Documents/product images repo"
OUT=tasks/marriott-hospital/outputs
declare -A WIN
WIN[door]=r3_door_s1.png
WIN[left]=r3_left_s3.png
WIN[right]=r3_right_s3.png
for panel in door left right; do
  src=$OUT/${WIN[$panel]}
  up=$OUT/r3_${panel}_up.png
  dh=$OUT/r3_${panel}_dh.png
  fin=$OUT/r3_${panel}_final.png
  echo "=== $panel : $src ==="
  python3 scripts/reupscale.py --image "$src" --out "$up" --creativity 0.5 --resemblance 0.6 --factor 2
  echo "[up] done"
  python3 scripts/dehalo.py --image "$up" --out "$dh"
  echo "[dehalo] done"
  python3 scripts/white_key.py --image "$dh" --out "$fin"
  echo "[white_key] $fin done"
done
echo "=== FINISH CHAIN COMPLETE ==="
ls -la $OUT/r3_*_final.png
