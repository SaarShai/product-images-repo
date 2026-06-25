---
nid: nogil7
title: "Composite"
type: step
x: 1180
y: 300
icon: "🧩"
summary: "Diff-mask composite — blend the edit back, keep the rest byte-exact"
gate: "outside-mask pixel delta == 0"
status: draft
tags: [repair, composite, gate]
---
# Composite

Blend the repaired region back into the original so everything outside the mask stays
byte-exact:

```
scripts/compose_fairy.py   # diff-mask composite + outside-mask pixel gate
```

A diff-mask composite restores the protected zone from the baseline pixel-for-pixel, so the
edit is the *only* thing that changed. This is the mechanism behind core law 7 (separate
generation-mask from blend-mask; outside-mask delta == 0) and it kills the pose-ghost a naive
whole-crop repaint leaves behind.

**Gate:** outside-mask pixel delta == 0.

Then go to [[verify|verify]].
