---
nid: n371rw
title: "Back to generation"
type: step
x: 400
y: 180
icon: "↩️"
summary: "Failed candidates return to Stage 2 to regenerate"
status: draft
tags: [reject, regenerate]
---
# Back to generation

Terminal for this map. Any candidate that fails the deterministic gates at
[[pass|pass]] is rejected here and handed **back to Stage 2 (Generation)** to produce
new attempts (more models × prompts × refs). It does not advance to the vision judge
or the board.

This keeps the select stage honest: only candidates that already clear the hard
machine checks consume judge and human attention. The regenerate loop lives in the
Stage 2 map; this node is just the hand-off out of Stage 3.
