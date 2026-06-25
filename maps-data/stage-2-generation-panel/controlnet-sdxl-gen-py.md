---
nid: n5dk4t
title: "controlnet_sdxl_gen.py"
type: reference
x: 660
y: 30
icon: "🛠️"
summary: "scripts/controlnet_sdxl_gen.py — SDXL inpaint + lineart ControlNet, geometry-exact"
status: draft
tags: [tool, script]
---
# controlnet_sdxl_gen.py

The geometry-exact generation tool: `scripts/controlnet_sdxl_gen.py`.

SDXL inpaint with an xinsir canny / lineart ControlNet conditioned on the
SVG-derived lineart, so the panel silhouette is fit **by construction** to the
target contour (region-IoU ≥ 0.85, holes left empty). This is how exact layout is
locked without asking a model to paint coordinates.

Drives the [[controlnet-lane|controlnet-lane]]. Detail: `docs/PIPELINE.md` (Stage 2).
