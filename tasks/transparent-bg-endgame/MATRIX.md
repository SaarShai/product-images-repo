# Experiment matrix v1 — advisor-merged (Sol xhigh, 2026-07-13)

Supersedes MATRIX-DRAFT.md (kept for history). Full advisor reply:
scratchpad recon/advisor-sol-ultra.md (also summarized in CALIBRATION.md v2).

## Canary-gated routes (run canaries FIRST; a failed canary ⇒ ROUTE_UNAVAILABLE, never faked)
- **O** = gpt-image-1 native alpha (deprecated upstream — verify empirically; fallback gpt-image-1.5 / chatgpt-image-latest, whichever canary passes)
- **F** = ~~Flux.2 native alpha~~ CANARY FAILED (no alpha param in fal/BFL schemas) → replaced by **O2 = chatgpt-image-latest** (canary ROUTE_OK, image-2-family quality, real alpha; see CANARIES.md). gpt-image-1.5 = spare.
- **C** = flat #00FF00 + chroma_key pipeline (verified baseline)
- **W** = white-bg R4 recipe + white_key + dehalo_edge (user-verified baseline)

## Subjects (2)
- **H** (hard-friendly): closed ink contours, pale off-white detail, 0.15-0.40mm thin features, one legitimate green detail, intentional negative spaces.
- **W** (watercolor-stress): deckled + soft wash edges, enclosed cavities, pale washes, one green motif, no intended outer glow.

## Prompt levels (2)
- **AA**: natural style-faithful watercolor edge; forbid halo/aura/shadow/paper-colored fringe; allow intentional soft wash.
- **HARD**: opaque closed outer contour; nothing feathers outside; no semi-transparent outer fade, glow, shadow. (Factual phrasing only — semantic framings like "die-cut sticker" proven harmful.)

## Generations: 4 routes × 2 prompts × 2 subjects × 2 replicates = 32 calls
Each master then yields 3 outputs: soft/natural baseline + 2 binary variants
from the 16-cell covering design (route×prompt ↔ pre/post-upscale binarize ×
erode 0/1/2 — exact assignment table in advisor reply §3). Total 96 outputs.

## Processing order (advisor-corrected; NEVER threshold-then-unmix)
soft key/matte → known-bg ridge unmix F=(a²F0+λD)/(a²+λ), λ(a)=0.04(1-a)²,
linear light → donor pad 2-4px → upscale (RGB neural / alpha monotone) →
threshold → optional signed-distance erode {0,1,2}px at final size.
Keep A_soft stored alongside binary deliverable (analysis state + wash-layer option).

## Gates
gate_battery v2 (donor-referenced halo, mm units, tri-state) on FINAL BYTES;
truth-deck recovery scores for D5; **style veto**: blind side-by-side vs
style ref — a clean hard-edge result that reads sticker/vector loses (user judges).
Win condition: all 4 subject/replicate blocks pass every high-severity gate,
no semantic component disappears, style passes. Rank by WORST image, not mean.
"No production route yet" is an allowed conclusion.

## Physical grounding
Panel width ~40cm ⇒ 4000px = 254ppi; 300ppi needs 4724px. All edge thresholds
in mm (0.085mm = 1px @300ppi). Final-size gating mandatory.

## Sequence
1. Canaries (running) → prune routes.
2. Truth deck (running) → calibrate D5 + contour displacement.
3. One candidate per surviving route×prompt on subject H → battery v2 + boards → **USER REVIEW STOP** (show early).
4. Full 32-gen matrix on approved directions; covering-design post variants.
5. Winner → pipeline script + skill update; loser evidence banked.
