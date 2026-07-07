---
schema_version: 2
title: "Marriott Hospital T2 method-matrix: gpt-image production winner; nano recompose kill"
type: fact
domain: image-gen
tier: semantic
confidence: 0.95
trust: user_confirmed
created: "2026-07-06"
updated: "2026-07-06"
verified: "2026-07-06"
sources: ["REVIEW/marriott-hospital/t2-FINALISTS-board.jpg", "tasks/marriott-hospital/outputs/t2_e*.png", "VERDICT-t2-consolidated.md"]
resource: "scripts/subgen.py"
supersedes: []
superseded-by: []
contradicts: []
tags: ["image-generation", "gpt-image", "nano-banana", "flux", "method-matrix", "marriott", "architecture", "watercolor", "style-transfer", "geom-fidelity"]
---

# Marriott Hospital T2: gpt-image production winner; nano recompose kill

**User verdict (2026-07-06):** E5 (gpt-image FREE via codex subgen, restyle-from-init) wins. **Reason:** edges properly defined, complete building silhouette (not cropped), intentional-made-from-geometry look — design reads as authored from the geometry, not post-hoc. Slight detail overhang (window sills, dome base, teddy arm) beyond left/right silhouette = positive (intentional-complete-building axis; overhang OK if slight).

**New style-bible axis:** "intentional complete building; slight-overhang permissible" — signals confident authorship, not leakage/error.

## Scorecard Summary

| Model / Route | Code | Paid Geom | Notes |
|---|---|---|---|
| gpt-image-2 (fal paid) | E10 | 0.9016 | Exact 832×1184; reference baseline |
| gpt-image (codex FREE) | E5 | ~95% of E10 | **Production pick:** edges, silhouette fidelity, restyle-from-init path |
| gpt-image guide-gen | E7 | 0.704 aspect | Works; aspect constraint validated |
| Kontext max tight geom | E8 | — | Tight geometry, flat art (no watercolor) |
| Kontext + MRWC LoRA | E6 | 0.826 | Watercolor, cream walls drift (geom penalty) |
| Flux.2-edit (style-ref gen) | — | — | Vetoed: style-reference-only path, 2nd structure failure (awning), not suitable for die-cut |
| Nano family (all tiers) | E9, E1–E4 | 0.705 | **Killed from die-cut pipeline:** aspect enum lacks tall 0.39 → recomposes all tall panels |

**Key observation:** E9 (nano-pro) reads as "complete building" because nano recomposed the aspect to ~1:1 square. That virtue is recompose-artifact, not inherent modeling. Must be reproduced via gpt-image path + user guidance, not via nano selection.

## Method-Matrix Details

### Closed: gpt-image family = production model

- **Free iteration:** codex CLI `subgen --provider openai` (E5 path)
- **Finals:** fal paid `gpt-image-2` (E10 path); user confirmed 95% parity on E5 sufficient for dailies
- **Restyle from init:** gpt-image free init → user feedback → restyle same seed = proven workflow
- **Reference:** geometry guide (canny SVG edges) + style refs (watercolor exemplars) → locks aspect, guides focal

### Open: MRWC LoRA disposition

- E6 (Kontext + MRWC LoRA): watercolor ✓, cream-walls drift (geom 0.826 vs target 0.90+)
- Action: measure whether LoRA cost (geom hit) justifies watercolor boost vs plain Kontext; likely droppable
- Caveat: only DOOR tested; left/right/stab panels pending

### Vetoed: Nano Banana (all tiers) from die-cut

- All nano instances recompose tall narrow panels (aspect 0.39 missing from enum)
- Aspect recompose→square is why E9 reads "complete"; not transferable to other models
- **Prevention:** aspect guard in gen harness; tall panels rejected if model lacks enum support

### Vetoed: Flux.2-edit as structure generator

- Role limit: style-reference generator only (image→style→apply-to-structure)
- 2nd structure failure on t2 (awning added; not user-guided)
- Route broken; would need structured control (LoRA / ControlNet) to lock geometry + style simultaneously
- **Prevention:** flux2 restricted to element-edit + restyle-already-approved-geometry paths

## Open Items (blockers for next phase)

1. **Emblem discipline:** two crosses persist
   - Dome beacon (1×+)
   - Facade badge (1×+)
   - Action: `emblem_gate.py` TBD; user to define per-type gating rule
   
2. **Result recovery:** falgen `.artifact.json` incomplete
   - t1 LoRA path unrecoverable (not logged in artifact)
   - Action: falgen must record full request args (model, LoRA, control_lora_scale, canny params)
   
3. **Codex gpt-image-2 access:** unknown
   - Can codex CLI reach gpt-image-2 (paid) for free-or-cheap test? 
   - Action: verify; impacts finals cost/speed tradeoff
   
4. **Panel coverage:** door only tested
   - Left, right, stab panels pending method-matrix validation
   - Action: run t3 with gpt-image on left/right/stab; confirm geom/style carry

## Pipeline Implications

- **Restyle loop closed:** gpt-image free init + user feedback + restyle same init ✓
- **One Kontext pass max:** multi-turn degrades; single style-refinement pass only
- **Geometry lock first:** guide-gen + SVG canny edges non-negotiable
- **No nano from die-cut:** aspect enum constraint is hard stop (no soft fallback)

## Next Phase Direction

User directive: drawing-board rebuild of workflow around gpt-image, with user guidance per approved t2 verdict.

Workflow contract TBD:
- Init generation (gpt-image free)
- User feedback loop (measured gates)
- Restyle or next panel (gpt-image free or paid finals)
- Emblem discipline
- Open panel coverage (left/right/stab)

## Related

- [[concepts/onepass-geometry-style-route-flux-control-lora]] — flux one-pass baseline (closed; gpt-image now primary)
- [[concepts/two-gate-acceptance-silhouette-iou-plus-vision-judge]] — measurement gates
- [[concepts/no-painted-text-vector-layer-or-omit]] — signage constraint
- [[index]]
