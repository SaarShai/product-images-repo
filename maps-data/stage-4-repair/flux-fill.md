---
nid: nlbq6c
title: "Flux Fill"
type: step
x: 660
y: 300
icon: "🖌️"
summary: "Flux Fill masked inpaint to redraw one element in place"
status: draft
tags: [repair, redraw, inpaint]
---
# Flux Fill

Redraw one element within its own footprint via masked inpainting:

```
scripts/edit.py --op redraw --element "the <thing>"
```

`edit.py` routes redraw-in-place to **Flux Fill** (masked). Masked inpaint keeps the edit
localized — the model only repaints inside the mask — which is what a redraw-in-place needs
so position and surroundings are preserved. In a busy watercolor scene this localization
matters: an unmasked instruction-edit engine repaints the whole crop and the diff seams, so
the masked Flux-Fill path with an element-silhouette mask is preferred.

Then go to [[mask|auto-mask + guardrail]].
