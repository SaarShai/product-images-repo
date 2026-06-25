---
nid: nsbr6x
title: "Route engine"
type: decision
x: 400
y: 300
icon: "🔀"
summary: "Branch to the repair engine that matches the operation"
status: draft
tags: [repair, routing, gate]
---
# Route engine

Branch by operation — the engine is fixed by the defect class, not re-derived per task
(routing table lives in `docs/PIPELINE.md` Stage 4). The four representative branches
shown on the map:

- **remove** → [[use-eraser|Bria eraser]] (`falgen.py --mode eraser`; `--free` = local LaMa).
- **redraw** → [[flux-fill|Flux Fill]] masked inpaint via `edit.py --op redraw`.
- **ghost / occlusion** → [[donor|mask-bounded external redraw donor]] (OpenAI via subgen) for
  broad ghost/haze in a busy scene.
- **blur** → [[sharpen|adaptive sharpen / reupscale]].

The remaining operations (not drawn, but routed the same way):

- **restyle + layout** → Flux.2 / `gen_styled.py`.
- **reshape element** → stretch-then-Kontext (PIL stretch → Flux Kontext cleanup → composite).
- **edit existing text** → `qwen_edit.py`.
- **exact-geometry redraw** → `controlnet_sdxl_gen.py`.
- **same element ×N (consistency)** → reference-lock (Flux.2 `image_urls` / IP-Adapter).
