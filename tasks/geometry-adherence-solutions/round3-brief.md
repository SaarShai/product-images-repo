# Round-3 consult: style failure, fold-seam continuity, geometry-input design

You are one of two independent advisors (you do not see the other's answer).
Context repo: /Users/za/Documents/product images repo
Experiment root: tasks/geometry-adherence-solutions/experiment-1/

## State (verified)

Staged hard-mask pipeline validated at experiment scope on the princess-n02
panel (640x1544): SDXL-inpaint hard paintable mask + canny CN on a
composition map + IP-Adapter + watercolor LoRA -> Stage-B low-denoise img2img
-> socket composite-back. Geometry perfect on all 8 gens (0 px outside
silhouette, 0.0% hole paint, byte-exact door composite). See
experiment-1/CONCLUSIONS.md.

USER VERDICT just arrived on the outputs (runs/B-s21-d050/final.png etc.):

1. **STYLE: "awful."** Muddy/dusty vs the luminous frontier reference images.
   Style stack was: SDXL base + generic watercolor LoRA
   (/Users/za/models-gen/loras/watercolor_v1_sdxl.safetensors) fused at 0.75
   + IP-Adapter-plus with the user's two approved refs
   (tasks/geometry-evidentiary-princess-n02/refs/princess style 01.png, 02.png)
   at scale 0.55 restricted to ONE style layer (up.block_0=[0,0.55,0]).
   Diagnosis hypothesis: LoRA+SDXL-base dominates; refs barely bind.

2. **FOLD SEAM divides the image.** The panel has a wavy fold line separating
   bottom and top subpanels (a PHYSICAL fold in the die-cut product, not a
   drawing boundary). Current output reads as a NEW building starting at the
   top subpanel. Root cause (verified by inspecting
   assets-640/control_canny.png and control_composition.png): the fold band
   is drawn as the SAME 4px white stroke as the die-cut contour, the arch,
   the slot, and the composition trace — indistinguishable stroke semantics.
   Plus the exemplar trace is itself discontinuous at the fold (wall+trees
   terminate above, separate towers below).

3. **USER DIRECTIVE: invest in the best possible geometry reference/input +
   instructions for image-gen models.** Current inputs are raster PNGs
   rendered from the authoritative SVG: binary silhouette/paintable masks,
   a canny-style stroke map of SVG geometry, an exemplar composition trace,
   a grey init canvas. User asks: image or SVG, which is better, and how to
   make the reference/input maximally effective.

## Questions (answer ALL, be concrete, commit to numbers/designs)

Q1 (style): Rank the levers to fix style, given the hard constraint that
geometry gates (hard mask, silhouette re-mask, socket composite) can be
re-applied AFTER any style pass, so the styler need not be geometry-safe:
 a. IP-Adapter full routing / higher scale, LoRA lowered or dropped
 b. Better SDXL fine-tune checkpoint (which?) instead of base+generic LoRA
 c. Stage-B restyle via a FRONTIER engine (gpt-image-2 / nano-banana img2img
    on the geometry-locked base, then re-mask + composite-back locally)
 d. Other (e.g., Flux + style LoRA, IP-Adapter on Flux)
Which gets closest to the luminous reference style with least new machinery?
Note repo memory: "Re-seat route" already proved frontier restyle-then-remask
gives style but erased controls; the difference NOW is we have byte-exact
composite-back + punch tools, so post-styling mechanical repair exists.

Q2 (fold seam): Prescribe the control-map redesign so the fold NEVER reads
as an architectural boundary but composition still respects it as a
no-focal-motif zone. Options to weigh: remove fold stroke entirely from both
maps; keep it only in the paintable/keep-clear channel (not the visual
control); dashed/faint stroke; exemplar re-registration so vertical
structures cross the fold; prompt language. Commit to one design.

Q3 (geometry-input design): Design the CANONICAL "geometry packet" for
image-gen models. Address:
 - SVG vs raster: models consume pixels; SVG stays source of truth. Given
   that, what raster ENCODINGS should the packet contain?
 - Stroke semantics: physical cut edge vs fold vs keep-clear vs cutout vs
   composition hint currently all identical white 4px. Propose a visually
   distinct encoding per semantic class (per-channel? per-map? stroke style?)
   and which maps feed which consumer (SDXL CN canny/depth/seg; frontier
   models as image-1 guide).
 - Should we add depth or segmentation/region-color maps (repo has a proven
   semantic color-region-map pattern for frontier models)?
 - Instruction text: what prompt/legend template should accompany the packet?
Deliverable: a concrete spec I can hand to a builder agent.

## Attached/readable images

- assets-640/control_canny.png (round-1 contour-only map)
- assets-640/control_composition.png (round-2 exemplar trace map)
- runs/B-s21-d050/final.png (current best, user-judged awful style + seam)
- tasks/geometry-evidentiary-princess-n02/refs/princess style 01.png (target style)

Answer in numbered sections Q1/Q2/Q3. Keep to the point; commit to one
recommended design each, with fallbacks only if load-bearing.
