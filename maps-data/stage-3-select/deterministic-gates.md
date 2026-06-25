---
nid: ndqnns
title: "Deterministic gates"
type: step
x: 140
y: 300
icon: "📏"
summary: "Hard machine gates: geom_gate + text_gate before any human or vision spend"
gate: "region-IoU≥0.85 (template) OR outside-mask delta==0 (edit); text-gate clean"
status: draft
tags: [gate, deterministic, geometry, text]
---
# Deterministic gates

The first, cheapest filter in Stage 3. Run the deterministic hard-gates on every
candidate **before** spending any vision-judge or human attention:

- `scripts/geom_gate.py` — geometry containment. For a template / die-cut task:
  **region-IoU ≥ 0.85** against the SVG contract. For an element-edit task:
  **outside-mask pixel delta == 0** (nothing outside the intended region moved).
- `scripts/text_gate.py` — text-gate clean (no leftover / hallucinated text artifacts).

Gate: **region-IoU≥0.85 (template) OR outside-mask delta==0 (edit); text-gate clean.**

A failing candidate never reaches the judge — it routes back to generation. A passing
candidate is necessary but **not** sufficient (law 4: metrics lie). Feeds the branch
at [[pass|pass]].
