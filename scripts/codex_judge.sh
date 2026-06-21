#!/usr/bin/env bash
# codex_judge.sh — run codex (GPT-5.5 vision) as a one-shot IMAGE judge.
# codex CAN see images via `-i`; the reliable non-interactive form is to pipe the
# prompt on stdin (a positional prompt collides with the variadic -i). Verified to
# catch objective defects (e.g. a stacked double-window) AND rate style/proportions.
#
# Usage:
#   scripts/codex_judge.sh "PROMPT (ask for one image only — DO NOT pass A/B pairs,
#                            they risk a label swap)" img1 [img2 ...]
#
# Prints codex's text answer on stdout. Requires the codex app/auth available on the
# device (if codex is closed, the call hangs/empties — run codex once interactively).
set -euo pipefail
if [ "$#" -lt 2 ]; then echo "usage: codex_judge.sh PROMPT IMG [IMG...]" >&2; exit 2; fi
prompt="$1"; shift
printf '%s\n' "$prompt" | codex exec -i "$@"
