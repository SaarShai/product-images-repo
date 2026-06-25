---
nid: nfunjz
title: "Assemble inputs"
type: step
x: 140
y: 300
icon: "🧩"
summary: "Build the prompt (no geometry words) + attach style-packet refs + geometry guide"
gate: "NO geometry words (SVG/contour/red zone/arch) in prompt; refs + geometry guide attached"
status: draft
tags: [generation, prompt, references]
---
# Assemble inputs

Assemble the three things every candidate needs before any model is called:

- the **prompt** — describing subject, style, mood — and *nothing about geometry*.
  No SVG, contour, red zone, keep-clear, or saloon-arch words. Geometry is locked
  by construction downstream, not by asking the model to paint coordinates.
- the **style-packet references** from Stage 1a — the actual attachable visual
  evidence (object vocabulary, line weight, density, lighting, material). Law:
  **reference beats prose** — these images drive the look, the prompt does not.
- the **geometry guide** from Stage 1b — the grey-body / coordinate-true lineart
  image that the model fills, which carries the panel aspect and keep-clear lanes.

Gate: **NO geometry words (SVG/contour/red zone/arch) in prompt; refs + geometry
guide attached**. Next: decide the lane at [[exact-geometry|exact-geometry]].
