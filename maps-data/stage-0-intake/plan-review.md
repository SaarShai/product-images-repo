---
nid: nbcote
title: "Plan review (human gate)"
type: decision
x: 1440
y: 300
icon: "🛂"
summary: "Human reviews plan + reference inventory BEFORE any spend"
gate: "human reviews plan + reference inventory BEFORE any spend"
status: draft
tags: [gate, human, review]
---
# Plan review (human gate)

The Stage 0 hard gate. A human reviews the emitted **PLAN.md** and the **reference
inventory** (asset-manifest.json) from [[emit-packet|emit-packet]] **before any
model budget is spent**. This is the whole point of the spine: force an upfront,
reviewable plan so the back of the pipeline doesn't explode into reactive repair
waves.

Gate: **human reviews plan + reference inventory BEFORE any spend.**

On approval, control passes out of Stage 0 into the first applicable downstream
stage chosen by the family router (e.g. 1a style packet for A–C, or straight to
Stage 4 repair for D–F). That hand-off is implied — it lands in the next stage map.

Spine reference: [[pipeline-spine|docs/PIPELINE.md]].
