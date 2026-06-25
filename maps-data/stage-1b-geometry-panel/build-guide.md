---
nid: n0n5mt
title: "Build guide"
type: step
x: 660
y: 300
icon: "🖼️"
summary: "build_trueaspect_base.py → true-aspect geometry-guide PNG for the model"
gate: "guide aspect == panel aspect"
status: draft
tags: [svg, geometry, guide]
---
# Build guide

Render the geometry into the image the model actually receives — a true-aspect
geometry-guide PNG (grey-body / coordinate-true lineart). This is **geometry by
construction**: the guide carries the panel's exact aspect and cutout positions,
so the model paints *into* the geometry instead of being asked to invent
coordinates.

```bash
scripts/build_trueaspect_base.py   # → true-aspect geometry-guide PNG
```

The guide's aspect ratio must equal the panel's aspect ratio — a narrow die-cut
panel (e.g. ~0.39) is something prompts alone cannot produce, but a true-aspect
guide locks it. A guide whose aspect drifts from the panel will warp every
candidate downstream, so that equality is the gate.

Gate: **guide aspect == panel aspect**. Workflow detail:
[[svg-template-workflow|docs/svg-template-illustration-workflow.md]]. Next, decide
drift handling at [[outset-needed|outset-needed]].
