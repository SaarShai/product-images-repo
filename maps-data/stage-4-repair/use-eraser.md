---
nid: nvtuvv
title: "Use eraser"
type: step
x: 660
y: 180
icon: "🧽"
summary: "Bria eraser removes an element and reconstructs the background in-style"
status: draft
tags: [repair, remove, eraser]
---
# Use eraser

Remove an element and let the engine reconstruct the background **in-style**:

```
scripts/falgen.py --mode eraser   # Bria; --free routes to local LaMa
```

Bria is the right tool for erasing a car / sign / stray text because it paints a plausible
in-style background into the hole. (Flux-Fill negatives are weak for removal — they heal
text back or add cars — so removal uses the dedicated eraser, not a redraw with a negative
prompt.) For big-area erases the leak gate is loosened to ~0.12.

Then go to [[mask|auto-mask + guardrail]] so the change is bounded before compositing.
