# GOAL — decide what to INSTALL locally for our image workflow (latest models/platforms incl. Flux 2)

## Outcome
A concrete, tiered **install plan** for this Mac that gives us a LOCAL, COMMERCIAL-SAFE pipeline for:
- **Masked / region-locked editing** ("change only X, nothing else") — true inpaint, not a composite hack
- **Exact geometry lock** (ControlNet: canny/lineart/depth/softedge) for SVG-template fitting
- **Style fidelity** — delicate watercolor / storybook (the historical weak point of local SDXL)
- **Anatomy fix** (crisp hands/5 fingers, faces, toes)
- **High-res output** (upscale without destroying watercolor)
- Scriptable/headless so it plugs into our automation (subgen-style)

## Hard constraints (measured this session)
- Hardware: **Apple M3 Max, 48GB unified, macOS (Darwin 25.5)**, MPS works.
- Disk: **~86GB free (91% full)** — install plan MUST fit; prefer quantized; flag total size.
- Commercial: user **sells** Screenery products → production assets need **commercial-permissive licenses**. Non-commercial models (e.g. Flux dev) OK for *experiments* only.
- Already installed: ComfyUI (cloned), torch 2.8 + MPS, diffusers 0.27.2 (OLD), transformers 4.39.3, SDXL base 1.0, xinsir canny-controlnet-sdxl, dreamshaper-8 + dreamshaper-8-inpainting. Missing: peft, openai SDK, IP-Adapter weights, loras, upscalers, Flux.

## Method
Fan out 5 parallel research streams (below), each a self-contained /goal. Synthesize → tiered PLAN.md (Tier0 have / Tier1 install-now-small / Tier2 Flux2 / Tier3 optional-large) that fits the disk budget, with exact download/install commands + sizes + licenses. Present for approval BEFORE large downloads (irreversible disk spend).

## done means
- [ ] 5 research streams returned + synthesized (sources cited)
- [ ] PLAN.md: tiered install list, each item w/ purpose + exact install cmd + size + license(commercial?) + M3-Max-MPS feasibility
- [ ] Total disk fits within budget (≤ ~60GB, leaving headroom); flag if not
- [ ] Clear top-pick stack + the ONE platform to drive it
- [ ] Presented for approval; nothing large downloaded without OK
