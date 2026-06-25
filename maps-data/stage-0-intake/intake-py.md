---
nid: nkhrad
title: "intake.py"
type: reference
x: 400
y: 450
icon: "🛠️"
summary: "scripts/intake.py — universal intake: classify family, inventory inputs, emit packet"
status: draft
tags: [tool, script]
---
# intake.py

The universal Stage 0 tool: `scripts/intake.py`.

It classifies the task family (A–F), inventories the inputs and their dimensions,
decides which downstream stages apply, and emits the BRIEF + PLAN + asset-manifest
with only the applicable stages. The legacy template-only path
`scaffold_template_task.py` is superseded by this for non-template tasks.

Drives [[classify-family|classify-family]], [[inventory-refs|inventory-refs]], and
[[emit-packet|emit-packet]]. Documented in the spine: [[pipeline-spine|docs/PIPELINE.md]].
