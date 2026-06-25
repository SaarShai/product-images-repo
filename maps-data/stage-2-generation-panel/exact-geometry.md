---
nid: nzbn3n
title: "Need pixel-exact contour fit?"
type: decision
x: 400
y: 300
icon: "❓"
summary: "Branch on whether the panel needs pixel-exact contour fit"
status: draft
tags: [decision, geometry]
---
# Need pixel-exact contour fit?

Branch on how tight the contour fit has to be for this panel.

- **Yes** — the panel needs pixel-exact contour fit (die-cut edges, holes, narrow
  apertures that must land on the SVG to the pixel) → take the ControlNet lane at
  [[controlnet-lane|controlnet-lane]], where SDXL + lineart ControlNet locks the
  silhouette by construction.
- **No** — exact-to-the-pixel fit isn't required at generation time (fit can be
  recovered later, or the panel is forgiving) → take the
  [[subscription-lane|subscription-lane]] for faster multi-model candidates.

Both lanes converge on [[fan-out|fan-out]] so multiplicity is always produced.
