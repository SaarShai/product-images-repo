#!/bin/bash
# C4 post-render: gate each raw (door_fill + overlay), collect numbers, build overlay board.
set -u
R="/Users/za/Documents/product images repo"
C="$R/tasks/workflow-rebuild/comfy/round-c4"
GEOM="$R/tasks/marriott-hospital/geometry/v3"
cd "$R"
mkdir -p "$C/gates" "$C/board"
RES="$C/round-c4-gate-results.json"
echo "[" > "$RES"
first=1
for raw in "$C"/raws/*.png; do
  [ -e "$raw" ] || continue
  name=$(basename "$raw" .png)
  ov="$C/gates/$name-doorfill-overlay.png"
  out=$(python3 scripts/door_fill_gate.py --image "$raw" --geom "$GEOM" --panel door --overlay "$ov" 2>/dev/null)
  df=$(echo "$out" | python3 -c "import sys,json;print(json.load(sys.stdin)['door_fill'])" 2>/dev/null)
  vd=$(echo "$out" | python3 -c "import sys,json;print(json.load(sys.stdin)['verdict'])" 2>/dev/null)
  [ $first -eq 0 ] && echo "," >> "$RES"; first=0
  printf '{"name":"%s","door_fill":%s,"verdict":"%s","overlay":"%s"}' "$name" "${df:-null}" "${vd:-ERR}" "$ov" >> "$RES"
  echo "$name  door_fill=$df  $vd"
done
echo "]" >> "$RES"
# overlay board of all C4 raws
python3 scripts/overlay_board.py --raws "$C/raws/*.png" --geom "$GEOM" --panel door \
  --out "$C/board/round-c4-overlay-board.jpg" --cols 4 2>/dev/null && echo "board: $C/board/round-c4-overlay-board.jpg"
