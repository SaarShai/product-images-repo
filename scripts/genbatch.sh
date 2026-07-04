#!/usr/bin/env bash
# genbatch.sh — supervised image-gen batch runner (retrospective fix, 2026-06-18).
#
# Why: ad-hoc `nohup … &` drivers kept dying silently (detached by a backgrounded
# wrapper) and a broad `pkill -f agy` killed in-flight gens AND sibling drivers.
# This runs a batch in its OWN process group, records the pgid, exposes `status`
# (counts ACTUAL raw.png files, not "proc alive"), and `stop` kills ONLY this
# batch's group — never a broad pkill of a shared binary.
#
# Usage:
#   scripts/genbatch.sh run  <name> <model> <base> <prompt> <svg> <count> <ref...>
#   scripts/genbatch.sh status <name>
#   scripts/genbatch.sh stop   <name>
# Output cells: tasks/<slug-from-base>/experiments-outset/<name>-s<N>/raw.png
# State: .genbatch/<name>.{pgid,log,outdir}
set -u
cd "$(cd "$(dirname "$0")/.." && pwd)"
GEN="scripts/geom_adherence_test.py"
STATE=".genbatch"; mkdir -p "$STATE"

cmd="${1:-}"; name="${2:-}"
[ -z "$cmd" ] || [ -z "$name" ] && { echo "usage: genbatch.sh run|status|stop <name> ..."; exit 2; }

case "$cmd" in
  status)
    od=$(cat "$STATE/$name.outdir" 2>/dev/null)
    pg=$(cat "$STATE/$name.pgid" 2>/dev/null)
    if [ -n "$pg" ] && pgrep -g "$pg" >/dev/null 2>&1; then alive=RUNNING; else alive=stopped; fi
    n=$(ls "$od"/${name}-s*/raw.png 2>/dev/null | wc -l | tr -d ' ')
    echo "batch=$name state=$alive raws=$n outdir=$od"
    [ -f "$STATE/$name.log" ] && tail -3 "$STATE/$name.log"
    ;;
  stop)
    pg=$(cat "$STATE/$name.pgid" 2>/dev/null)
    [ -n "$pg" ] && kill -TERM -"$pg" 2>/dev/null && echo "stopped pgid $pg (only this batch)" || echo "no live pgid for $name"
    ;;
  run)
    model="$3"; base="$4"; prompt="$5"; svg="$6"; count="$7"; shift 7
    refs=("$@")
    slug=$(echo "$base" | sed -E 's|tasks/([^/]+)/.*|\1|')
    outdir="tasks/$slug/experiments-outset"
    echo "$outdir" > "$STATE/$name.outdir"
    log="$STATE/$name.log"; : > "$log"
    # run the whole loop in its own session/process group, detached
    setsid bash -c '
      GEN="'"$GEN"'"; OUT="'"$outdir"'"; NAME="'"$name"'"; MODEL="'"$model"'"
      BASE="'"$base"'"; PROMPT="'"$prompt"'"; SVG="'"$svg"'"; CNT="'"$count"'"; LOG="'"$log"'"
      REFS=('"$(printf '%q ' "${refs[@]}")"')
      echo "pgid $$" >> "$LOG"
      for n in $(seq 1 "$CNT"); do
        id="${NAME}-s${n}"; dir="$OUT/$id"
        if [ -f "$dir/raw.png" ]; then echo "[skip] $id" >> "$LOG"; continue; fi
        for a in 1 2 3; do
          python3 "$GEN" --id "$id" --model "$MODEL" --map "$BASE" --prompt "$PROMPT" \
            --refs "${REFS[@]}" --svg "$SVG" --outdir "$OUT" --timeout 360 >/dev/null 2>&1
          [ -f "$dir/raw.png" ] && break
        done
        echo "[done] $id $([ -f "$dir/raw.png" ] && echo OK || echo FAIL)" >> "$LOG"
      done
      echo "BATCH $NAME DONE" >> "$LOG"
    ' &
    pg=$!
    echo "$pg" > "$STATE/$name.pgid"
    echo "launched batch=$name pgid=$pg model=$model count=$count"
    echo "  status: scripts/genbatch.sh status $name"
    echo "  stop:   scripts/genbatch.sh stop $name"
    ;;
  *) echo "unknown cmd: $cmd"; exit 2 ;;
esac
