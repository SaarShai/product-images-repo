---
nid: n40scw
title: "Re-curate refs"
type: step
x: 660
y: 180
icon: "🔁"
summary: "Add or swap reference images to fix the captured-style gap"
status: draft
tags: [style-packet, references]
---
# Re-curate refs

The packet missed part of the real style ([[inspect-packet|inspect-packet]] → No). Fix the
*inputs*, not the output: add or swap reference images in `tasks/<task>/refs/` so the gap is
covered — e.g. pull in refs that show the missing line weight, density, lighting, or material,
not just another image in the right palette.

Then loop back to [[build-packet|build-packet]] to regenerate the contact + exemplar sheets and
re-inspect. This is the only loop in the stage; it repeats until inspection passes.
