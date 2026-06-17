# Review brief — exact-geometry illustration

## Problem
Generate a tall-narrow (viewBox 767x2602, ~1:3.4) watercolor "space control-panel" illustration whose
geometry matches an SVG EXACTLY: outer contour + top-edge notch + 3 hexagonal openings + 1 long
vertical slot, at precise coordinates, with the openings rendered as illustrated bevelled rims (the
user explicitly likes the model-painted rim look; rejects a flat code-punched hole).

## Hard constraints
- Subscription-only generation, NO API keys: OpenAI "image 2"/gpt-image-2 via `codex exec - -i <imgs>`;
  Google Nano Banana via `agy` (native generate_image tool; max 3 input images; aspect enum only;
  cannot pick Pro vs 2; no resolution knob). render-studio (API) is OUT.
- Local Mac: torch 2.8 MPS, 48GB RAM, 99GB free. diffusers + ControlNet feasible. ComfyUI installable.

## What we built (scripts/)
- svg_geometry.py — robust SVG path parser (handles arcs/smooth/leading-dot; fixed a hang).
- svg_classify.py — role classifier (contour/paintable/cutout via containment+bite+polyline-closure) + manifest gate + map renderers (white/filled/lineart/magenta/preview).
- svg_geometry_check.py — VERIFIER: per-opening white-IoU + paint-bleed + outside-contour + overlay + json. JUST FIXED a registration bug (was mapping full viewBox onto the contour bbox → ~7% error on every number; now maps SVG contour bbox → detected panel bbox).
- geom_adherence_test.py — runner: generate (codex|agy) -> auto-register panel -> measure -> record.
- exact_bevel_composite.py — hybrid backstop: re-seat openings at exact coords + illustrated bevel.
- PIPELINE.md + LOOP.spec — staged pipeline (structure=code, style=model) + verify loop (gate mean_iou>=0.85 -> N=6 -> hybrid backstop); loop_lint clean.

## Measured (corrected, contour-registered white-IoU; rimmed-output ceiling ~0.79 = hybrid)
- gpt-image best-of-6: 0.483 (beautiful, drifts). E1 filled-base+contract: 0.400. free-redraw: 0.006.
- Nano Banana: ~0.00 white-IoU (BEST look + best relative-layout faithfulness, but openings drift most off exact SVG coords; smaller+recentred).
- hybrid backstop: 0.787 (exact placement by construction, but DEGRADES art — smears controls near openings, calm erased zones).
- Conclusion: NO pure subscription model hits exact coordinates, even best-of-N.

## Research recipe (converged across OpenAI/Gemini + 2 ComfyUI waves)
ControlNet locks structure: Canny/Lineart (contour+cutout edges) + MLSD (straight slot/border) +
low-weight Depth/Normal (the bevel rim relief), as MultiControlNet or ControlNet-Union; start_percent=0
(lock from step 0), end_percent ~0.8 (let watercolor bloom late). For pixel-exact cutouts:
ControlNet-Inpaint / masked-latent (SetLatentNoiseMask) + DifferentialDiffusion for soft graduated rims.
IP-Adapter carries watercolor style. Native aspect (e.g. 512x1738) — solves the aspect cap that
gpt-image/Nano can't (their max portrait is ~1:1.5 / 9:16, ours is 1:3.4). Note: one ComfyUI research
synthesis got prompt-injected (ignored).

## Status of generation tracks
- diffusers ControlNet (T1): running, no image yet.
- ComfyUI (ControlNet+IPAdapter): installs/downloads still running (~5.8GB), no image yet.

## Ask
Critique the approach, the research conclusions, and the results. Find flaws, blind spots, wrong
assumptions. Propose the most reliable, efficient SOLUTION(s) for exact geometry + illustrated rims +
good watercolor on THIS subscription/local Mac setup. Be concrete (models, controlnets, params,
pipeline). Challenge whether ControlNet is right, whether there's a simpler path, and how to handle
the extreme 1:3.4 aspect + the rimmed-opening metric ceiling.
