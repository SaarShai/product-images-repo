---
nid: ny86gb
title: "Safe-pocket plan (gate)"
type: step
x: 1180
y: 300
icon: "🚦"
summary: "GATE — guide aspect == panel; red zones hold only quiet/infrastructure"
gate: "guide aspect == panel; red zones contain only quiet/infrastructure"
status: draft
tags: [skyline, gate, keep-clear, preflight]
---
# Safe-pocket plan (gate)

The Stage 1b exit gate for skyline geometry. Two conditions must both be TRUE
before generation may spend:

1. **Guide aspect == panel.** The geometry guide handed to the model carries the
   exact per-panel aspect from the `.spec.json` (so even a narrow side panel is
   reproduced, not squared off). A preflight asserts guide aspect equals panel
   aspect — a mismatch fails the gate.
2. **Red zones contain only quiet/infrastructure.** The red dashed keep-clear
   lanes and blue separators may hold white sky, plain wall/facade texture, rail,
   water, or a solid train body — never a statue, sign, face, text, distinctive
   roof tip, or named landmark detail. Specific recognizable features sit in the
   safe pockets away from cut lines and seams.

Gate: **guide aspect == panel; red zones contain only quiet/infrastructure**.
Verified with [[skyline-panel-py|scripts/skyline_panel.py]] checks against the
spec, then the real SVG is overlaid and measured afterward.
