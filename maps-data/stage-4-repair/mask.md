---
nid: n291gl
title: "Mask + guardrail"
type: step
x: 920
y: 300
icon: "🎯"
summary: "Auto-mask the target, then guardrail it before any spend"
gate: "mask contains target, no leak (mask_check exit 0)"
status: draft
tags: [repair, mask, gate]
---
# Mask + guardrail

Bound the edit to the target before compositing:

```
scripts/automask.py     # text → tight mask (fal SAM-3) + cache
scripts/mask_check.py   # pre-spend guardrail: containment / leak (exit 2 on fail)
```

`automask.py` produces a tight mask from a text description; `mask_check.py` is the
pre-spend gate that confirms the mask actually contains the target and does not leak onto
protected regions. This is the #1 bottleneck-killer — it stops eyeballing mask coordinates
and refuses to spend on a bad mask.

**Gate:** mask contains the target with no leak — `mask_check.py` exits 0.

Then go to [[composite|composite]].
