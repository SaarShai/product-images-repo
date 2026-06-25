---
nid: nk66ob
title: "subgen.py"
type: reference
x: 660
y: 570
icon: "🛠️"
summary: "scripts/subgen.py — subscription image gen (OpenAI + Nano Banana)"
status: draft
tags: [tool, script]
---
# subgen.py

The subscription image-generation tool: `scripts/subgen.py`.

It is the single path for subscription gen — OpenAI (Codex) + Nano Banana (Antigravity
`agy`) — race-safe discovery, process-group kill on timeout, retry, validated output.
Always drive subscription gen through it; never run codex/agy ad hoc.

It is fed the style-packet references + the geometry guide (reference beats prose),
with **no geometry words** in the prompt. Drives the
[[subscription-lane|subscription-lane]]. Detail: `docs/PIPELINE.md` (Stage 2).
