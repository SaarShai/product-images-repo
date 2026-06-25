---
nid: m9xic3
title: "Stage 2 — Generation (SVG die-cut panel)"
type: map
kind: process
nodes:
  - assemble-inputs
  - exact-geometry
  - controlnet-lane
  - subscription-lane
  - fan-out
  - deterministic-gate
  - subgen-py
  - controlnet-sdxl-gen-py
edges:
  - {from: assemble-inputs, to: exact-geometry, label: ""}
  - {from: exact-geometry, to: controlnet-lane, label: "Yes"}
  - {from: exact-geometry, to: subscription-lane, label: "No"}
  - {from: controlnet-lane, to: fan-out, label: ""}
  - {from: subscription-lane, to: fan-out, label: ""}
  - {from: fan-out, to: deterministic-gate, label: ""}
  - {from: subscription-lane, to: subgen-py, label: "", route: smoothstep}
  - {from: controlnet-lane, to: controlnet-sdxl-gen-py, label: "", route: smoothstep}
---
# Stage 2 — Generation (SVG die-cut panel)

Produce candidate artwork for a family-A SVG die-cut panel, fed with the style
packet (1a) + geometry guide (1b). One branch decides whether the panel needs
pixel-exact contour fit (ControlNet lane) or can take the subscription multi-model
lane; both converge on a fan-out that prioritizes multiplicity over one-shot, then
hand to a deterministic gate before Stage 3.

Two laws govern every node here and are never re-derived:
- **Reference beats prose** — drive generation with the reference IMAGES + the
  geometry guide, never description alone.
- **Never put geometry words in the prompt** — no SVG, contour, red zone, or
  saloon-arch terms; geometry is locked by construction (the guide / ControlNet),
  not by asking the model to paint coordinates.

Tools: [[subgen-py|scripts/subgen.py]] (OpenAI + Nano Banana), `scripts/falgen.py`,
`scripts/falbatch.py`, `scripts/run_matrix.py`,
[[controlnet-sdxl-gen-py|scripts/controlnet_sdxl_gen.py]], `scripts/scout.py`.
Detail: `docs/PIPELINE.md` (Stage 2).

**PROVEN — architectural watercolor panel (cap-juluca 2026-06-24):** geometry guide
(cream silhouette + element zones, rendered from real SVG path data with `rsvg-convert`)
fed as image-1 + real photo refs + watercolor prose → strong result on attempt 1, no
watercolor reference needed. Use **`subgen.py --provider openai`** for polished
architectural watercolor; **nano is too loose/sketchy** for this stage.
