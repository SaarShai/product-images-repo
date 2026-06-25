---
nid: nnbjj3
title: "edit.py"
type: reference
x: 140
y: 450
icon: "🛠️"
summary: "Tool: one-command self-healing edit dispatcher"
status: draft
tags: [tool, repair]
---
# edit.py

The one-command entry point for a localized element edit. It chains the whole inner loop so
the operator runs a single command:

```
scripts/edit.py --src IMG --op remove|redraw --element "the yellow taxi" [--box x0,y0,x1,y1] [--free]
```

Pipeline inside: automask → mask guardrail → routed engine → diff-mask pixel gate → perceptual
leak gate → OCR text gate → VLM judge → auto-repair stray text → provenance JSON sidecar.

Cited path: `scripts/edit.py`. Realizes [[diagnose-defect|diagnose]] → route → [[mask|mask]]
→ [[composite|composite]] → [[verify|verify]] as one call. SOP: the `element-edit` skill.
