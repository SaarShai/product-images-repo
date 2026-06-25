---
nid: n2wyi1
title: "Emit plan packet"
type: step
x: 1180
y: 300
icon: "📦"
summary: "Write BRIEF.md + PLAN.md + asset-manifest.json"
gate: "BRIEF + PLAN + manifest written"
status: draft
tags: [intake, artifact]
---
# Emit plan packet

Write the three reviewable Stage 0 artifacts into `tasks/<task>/`:

- **BRIEF.md** — the universal brief (what to make, constraints, the requirements
  ledger captured upfront).
- **PLAN.md** — the staged plan, containing only the stages the family from
  [[classify-family|classify-family]] actually needs, each with its own per-stage gate.
- **asset-manifest.json** — the inventoried references (with dims) plus any
  precursor generated at [[generate-missing-ref|generate-missing-ref]].

The `reference-style-packet` skill is the natural next step in 1a — it turns these
inventoried refs into an attachable visual style packet for the generation stages.

Gate: **BRIEF + PLAN + manifest written** (all three present). Then the human gate
at [[plan-review|plan-review]]. Emitted by [[intake-py|scripts/intake.py]].
