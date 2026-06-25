---
nid: n9f3o6
title: "Receive brief"
type: step
x: 140
y: 300
icon: "📥"
summary: "Take in the task: description + references (+ optional SVG / base image)"
status: draft
tags: [intake, brief]
---
# Receive brief

The entry point. Collect the raw task as stated by the user:

- a **description** of what to make;
- **reference images** that anchor the style/subject (law 0: reference beats prose);
- *optionally* an **SVG template** / dieline (signals a geometry-bearing family A or B);
- *optionally* a **base image** to edit (signals a repair / element-edit / upscale family D–F).

No spend happens here — this is pure capture. The `requirements-ledger` skill should
already be extracting every stated intent into a user-visible ledger so nothing the
user asked for is silently dropped. The brief feeds [[classify-family|classify-family]].

See the spine for the universal stage contract: [[pipeline-spine|docs/PIPELINE.md]].
