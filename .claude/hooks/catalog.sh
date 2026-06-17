#!/usr/bin/env bash
# ALWAYS-catalog gate: on every Stop / SubagentStop, reconcile the results library
# from on-disk truth. Non-blocking (detached) + lock-guarded so it never stalls a
# turn and never piles up. Disk is the source of truth; results_db.py is idempotent,
# so a result produced by ANY track (workflow, background bash, subagent) is folded
# in shortly after it lands — cataloging cannot depend on the model remembering to run it.
set -u
REPO="/Users/za/Documents/product images repo"
cd "$REPO" 2>/dev/null || exit 0
[ -f scripts/results_db.py ] || exit 0   # graceful no-op until the curator ships the script

LOCK="/tmp/np01_catalog.lock"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then
  exit 0   # a reconcile is already running
fi

nohup bash -c '
  echo $$ > "'"$LOCK"'"
  cd "'"$REPO"'" || exit 0
  python3 scripts/results_db.py >/tmp/np01_catalog.out 2>&1
  python3 scripts/build_dashboard.py >>/tmp/np01_catalog.out 2>&1
  rm -f "'"$LOCK"'"
' >/dev/null 2>&1 &
exit 0
