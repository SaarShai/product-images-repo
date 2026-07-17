# Geometry adherence — architecture decision phase

Opened 2026-07-17, after princess-n02 evidentiary run closed NEGATIVE
(prompt+outset-guide route: iou 0.120, cutouts painted 71-98%).

## Goal
Decide the architecture that yields BOTH exact geometry (silhouette + clean
cutouts + socket respect) AND full reference style, then propose one frozen
cheap experiment. No gen spend this phase.

## Known facts (measured, from prior runs)
- Prompt+outset-guide: FAILS geometry (iou 0.120, cutouts 71-98% painted). Systematic.
- SDXL-inpaint + canny ControlNet on SVG lineart: region-IoU 1.0, holes empty
  (scripts/controlnet_sdxl_gen.py) — style gap is the weakness.
- Re-seat route: exact geometry 0.91 + gorgeous body, but erases controls.
- Local SDXL + watercolor-LoRA + IP-Adapter: competitive AND free (banked).
- Finding C OPEN: no composite-embedded-raster-back step → fixed-element
  sockets always "violated" by any full-panel gen.
- Style requires reference IMAGES as inputs, never prose (hard rule).

## Candidate lanes (diverge)
1. One-stage: ControlNet geometry + style conditioning (IP-Adapter/LoRA) at gen time.
2. Two-stage: geometry-exact base (CN) → style re-render pass w/ measured silhouette-IoU gate.
3. Gen-loose (frontier model, best style) → mechanical enforcement (silhouette mask,
   punch holes, composite-back) — risk: "cut" look (truncated-spires defect class).
4. Hard-mask inpainting (Flux Fill / SDXL inpaint): paintable region only, geometry
   by construction + style ref.
5. Region-map semantic guide + frontier gen (prompt-adjacent; weakest evidence).

## Lanes dispatched
- A: repo capability inventory (Explore)
- B: external SOTA survey (research-lite)
- C: advisor Sol (codex exec, main-shell)
- D: advisor Kimi K3 (pi_agents)
- Synthesis: main loop (Fable)

## Status 2026-07-17: all 4 lanes complete → SYNTHESIS.md
Decision: staged hard-mask architecture. Experiment designed, awaiting user
authorization. done-means items 1-4 met; item 5 = SYNTHESIS.md proposal.

## done means
1. Inventory table w/ measured numbers on disk.
2. SOTA survey on disk.
3. Sol + Kimi verdicts on disk.
4. Synthesis: chosen lane, composite-back design, per-defect-class gate list.
5. Proposed next frozen experiment (awaiting user authorization). Zero gen spend.
