---
nid: nibedt
title: "Build comparison board"
type: step
x: 920
y: 300
icon: "🖼️"
summary: "style_board.py: full-size side-by-side of ALL candidates (never low-res)"
gate: "ALL candidates shown at full size (never a low-res board)"
status: draft
tags: [board, review, fullsize]
---
# Build comparison board

Assemble the full-size comparison board with `scripts/style_board.py`: a
side-by-side of **every** surviving candidate at **full resolution**.

Law 6: show full-size, all candidates. Never decide style or sharpness from a
low-res thumbnail board — sharpness and fine-detail differences vanish at thumbnail
scale, so a low-res board silently biases the pick. The board must link every
candidate at full size, not a sample.

Gate: **ALL candidates shown at full size (never a low-res board).**

The completed board is handed to the human at [[human-pick|human-pick]].
