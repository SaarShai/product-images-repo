---
nid: n4j6uv
title: "ControlNet lane"
type: step
x: 660
y: 180
icon: "📐"
summary: "controlnet_sdxl_gen.py — SDXL + lineart ControlNet, geometry-exact"
gate: "region-IoU ≥ 0.85"
status: draft
tags: [generation, controlnet, geometry]
---
# ControlNet lane

The geometry-exact path. Run [[controlnet-sdxl-gen-py|scripts/controlnet_sdxl_gen.py]]
— SDXL inpaint with a lineart ControlNet conditioned on the SVG-derived lineart, so
the panel silhouette is locked **by construction**, not by hope. This realizes the
spine law that exact layout comes from raster/ControlNet, never from asking a model
to paint coordinates.

Gate: **region-IoU ≥ 0.85** — a measured silhouette overlap against the target
contour. A passing number is still not acceptance on its own (look at the overlay),
but it is the hard floor before this lane's candidates proceed.

Then fan out for multiplicity at [[fan-out|fan-out]].
