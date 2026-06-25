---
nid: npr53s
title: "Donor (external redraw)"
type: step
x: 660
y: 420
icon: "👻"
summary: "Mask-bounded external redraw donor for broad ghost/haze/occlusion in a busy scene"
status: draft
tags: [repair, ghost, donor]
---
# Donor (external redraw)

For a broad ghost / haze / occlusion artifact in a busy scene, the localized inpaint
engines seam. The working approach is a **mask-bounded external redraw donor**: generate a
clean redraw of the affected region with an external model and harvest only the masked area
as a donor patch.

```
scripts/subgen.py   # OpenAI generation of the donor plate
```

Critically, keep **two separate masks**: the *generation mask* (the broad region handed to
the donor model so it has context to paint coherently) and the final *blend mask* (the tight
region actually composited back). Conflating them is what makes the blend seam. See
[[mask-bounded-donor|the mask-bounded donor concept]].

Then go to [[mask|auto-mask + guardrail]].
