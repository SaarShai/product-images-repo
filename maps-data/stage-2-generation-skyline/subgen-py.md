---
nid: nmyevj
title: "subgen.py"
type: reference
x: 660
y: 450
icon: "🛠️"
summary: "scripts/subgen.py — subscription image gen (OpenAI + Nano Banana), the single gen path"
status: draft
tags: [tool, script]
---
# subgen.py

`scripts/subgen.py` — the single subscription image-generation path (OpenAI codex +
Antigravity Nano Banana). Always drive generation through it rather than calling the
underlying CLIs ad-hoc; it handles race-safe discovery, retry, and validation.

In this stage it powers the cheap low-res scouts at [[scout|scout]] and the full-res
≥3-attempt set at [[polish|polish]]. Pair it with `scripts/run_matrix.py` for the
experiment matrix and `scripts/falbatch.py` for parallel fan-out.

Always feed reference IMAGES + the geometry guide, and never put geometry words in
the prompt (laws of this stage). Workflow source of truth:
[[skyline-workflow|docs/skyline-template-illustration-workflow.md]].
