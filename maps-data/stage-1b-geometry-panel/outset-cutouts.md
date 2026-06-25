---
nid: ntf9uk
title: "outset-cutouts"
type: step
x: 1180
y: 180
status: draft
summary: "buffer internal cutouts outward to absorb drift"
---

# outset-cutouts

Run `scripts/outset_cutouts.py` to write a variant SVG whose internal cutouts are buffered outward by N px — enlarges the empty keep-clear zone so cut-drift can't bite. Then [[verify-coords|verify-coords]].
