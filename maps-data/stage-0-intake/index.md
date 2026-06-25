---
nid: ml4oym
title: "Stage 0 — Intake & Plan"
type: map
kind: process
nodes:
  - receive-brief
  - classify-family
  - inventory-refs
  - refs-complete
  - generate-missing-ref
  - emit-packet
  - plan-review
  - intake-py
  - pipeline-spine
edges:
  - {from: receive-brief, to: classify-family, label: ""}
  - {from: classify-family, to: inventory-refs, label: ""}
  - {from: inventory-refs, to: refs-complete, label: ""}
  - {from: refs-complete, to: generate-missing-ref, label: "No"}
  - {from: refs-complete, to: emit-packet, label: "Yes"}
  - {from: generate-missing-ref, to: emit-packet, label: ""}
  - {from: emit-packet, to: plan-review, label: ""}
  - {from: receive-brief, to: pipeline-spine, label: "", route: smoothstep}
  - {from: classify-family, to: intake-py, label: "", route: smoothstep}
---
# Stage 0 — Intake & Plan

The universal "from scratch" stage. One image task = one pass through the
pipeline; Stage 0 runs every time. It classifies the task family (A–F), inventories
and validates references, decides which downstream stages apply, and emits a
reviewable plan + asset manifest. Nothing spends model budget until a human
reviews the plan and reference inventory at [[plan-review|plan-review]].

Tooling: [[intake-py|scripts/intake.py]]. Spine: [[pipeline-spine|docs/PIPELINE.md]].
