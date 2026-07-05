#!/bin/zsh
set -e
cd "/Users/za/Documents/product images repo"
O=tasks/marriott-hospital/outputs
typeset -A WIN
WIN[door]=r9d_door_cut.png
WIN[left]=r10_left_c2_cut.png
WIN[right]=r10_right_c1_cut.png
for p in door left right; do
  src=$O/${WIN[$p]}
  echo "=== $p : $src ==="
  python3 scripts/reupscale.py --image "$src" --out $O/final_${p}_up.png --creativity 0.5 --resemblance 0.6 --factor 2
  echo "[up] done"
  python3 scripts/dehalo.py --image $O/final_${p}_up.png --out $O/final_${p}_dh.png
  python3 scripts/white_key.py --image $O/final_${p}_dh.png --out $O/final_${p}.png
  echo "[final] final_${p}.png"
done
echo "=== FINISH DONE ==="
