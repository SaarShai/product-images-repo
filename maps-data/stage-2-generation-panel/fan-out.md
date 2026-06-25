---
nid: nijb53
title: "Fan out"
type: step
x: 920
y: 300
icon: "🔀"
summary: "run_matrix.py + falbatch.py — multi-model × multi-prompt × ≥3 attempts/variant"
gate: "≥3 attempts per input variation; spread over one-shot"
status: draft
tags: [generation, fanout, matrix]
---
# Fan out

Maximize multiplicity. Drive `scripts/run_matrix.py` (the experiment matrix:
multi-model × multi-prompt) and `scripts/falbatch.py` (parallel queue fan-out) so
every input variation gets multiple attempts in parallel rather than a single
one-shot. `scripts/scout.py` can probe cheaply before a full spread.

Gate: **≥3 attempts per input variation; spread over one-shot** — the spine
prioritizes multiplicity over a single lucky generation; selection (Stage 3) needs a
real candidate set to choose from.

Hand the full candidate set to [[deterministic-gate|deterministic-gate]].
