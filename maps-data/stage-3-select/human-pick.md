---
nid: nckchw
title: "Human pick (gate)"
type: step
x: 1180
y: 300
icon: "🛂"
summary: "User picks the winner from the full-size board"
gate: "user picks the winner from the full-size board"
status: draft
tags: [gate, human, pick]
---
# Human pick (gate)

The Stage 3 hard gate and exit. After the deterministic gates and the vision judge
have narrowed the field, the **user picks the winner** from the full-size board built
at [[build-board|build-board]].

Aesthetics are not rankable by a metric or a VLM (the judge can rank geometry, not
taste), so the final selection is a human decision — made on the full-size board, all
candidates visible.

Gate: **user picks the winner from the full-size board.**

On selection, the chosen candidate advances out of Stage 3 to the next applicable
stage (4 Repair/Refine or 5 Finalize/Export). Spine: `docs/PIPELINE.md`.
