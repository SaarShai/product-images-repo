---
nid: napff7
title: "Generate missing reference"
type: step
x: 1180
y: 180
icon: "🪄"
summary: "Precursor: generate a needed reference first (stage 1c)"
gate: "user approves precursor"
status: draft
tags: [precursor, references, stage-1c]
---
# Generate missing reference

When the brief needs a reference that doesn't exist (e.g. a clean full building
plate, an exemplar in the target style), generate it FIRST as its own mini-task,
then feed it downstream as an anchor. This is stage **1c** of the spine, reached
from the **No** branch of [[refs-complete|refs-complete]].

This embodies the core law *reference beats prose — missing reference ⇒ generate
it as a precursor*. The generated image is logged as a ref in the manifest.

Gate: **user approves precursor** — a human signs off on the generated reference
before it is used as an anchor (you don't silently anchor on an unreviewed
generation). Once approved, it joins the inputs and flows to
[[emit-packet|emit-packet]].
