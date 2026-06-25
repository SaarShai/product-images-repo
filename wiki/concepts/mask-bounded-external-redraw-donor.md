---
schema_version: 2
title: "Mask-Bounded External Redraw Donor"
type: concept
domain: "product-images"
tier: semantic
confidence: 0.9
trust: user_confirmed
created: "2026-06-23"
updated: "2026-06-23"
verified: "2026-06-23"
sources:
  - tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png
  - tasks/berlin-hotel-base/wave3_tower_foreground_repair/results/wave3_feedback_board.png
  - tasks/berlin-hotel-base/wave3_tower_foreground_repair/results/wave3_shortlist_verification.txt
  - tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/method_notes.md
  - tasks/berlin-hotel-base/wave5_bridge_stairs_repair/results_v2/bridge_stairs_v2_board.png
  - tasks/berlin-hotel-base/wave6_bridge_stairs_openai_donor/results/bridge_stairs_openai_donor_board.png
  - tasks/berlin-hotel-base/wave6_bridge_stairs_openai_donor/results/stair_architecture_under_foliage_masked.png
  - tasks/berlin-hotel-base/wave7_hotel_roof_facade_repair/results/hotel_roof_facade_right_side_floor_context_board.png
  - tasks/berlin-hotel-base/wave7_hotel_roof_facade_repair/results/hotel_roof_facade_right_side_floor_context_verification.txt
  - tasks/berlin-hotel-base/wave7_hotel_roof_facade_repair/results/v11_right_parapet_precise_reinforced.png
supersedes: []
superseded-by:
contradicts: []
tags:
  - image-generation
  - localized-repair
  - openai
  - bounded-composite
  - task-retrospective
---

# Mask-Bounded External Redraw Donor

## Summary

For localized defects in a finished watercolor illustration, generate a broader
external redraw as a donor, then composite only the user-marked issue regions
back onto the banked baseline through a feathered mask. Use this when
conservative local cloning/inpainting removes pixels but leaves synthetic
smears, when the defect is a broad ghost/haze artifact that benefits from model
resynthesis, or when the defect is semantic continuity plus occlusion, such as
stairs or architecture that must continue behind trees.

This works because the image model can rebuild coherent local content across the
whole defect, while the final candidate remains mechanically bounded by the mask
so that unrelated artwork stays byte-identical.

It is especially useful for occlusion problems because manual linework or clone
patches tend to draw the object and the occluder separately, while the donor
edit can redraw the object/foliage relationship together.

For repeated architectural structures such as hotel windows or floor grids, keep
the generation mask and the final blend mask separate. A broad generation mask
can help the model understand the roof/parapet, but the final composite should
use a tighter mask plus protected-zone gates so that adjacent repeated structure
is restored from the banked baseline.

## Evidence

- User feedback on the wave3 feedback board: the bottom-right `S09 OpenAI
  redraw` candidate was "near perfect".
- Accepted candidate:
  `tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png`.
- External probe notes:
  `tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/external_edit_probe/method_notes.md`.
- Verification:
  `tasks/berlin-hotel-base/wave3_tower_foreground_repair/results/wave3_shortlist_verification.txt`
  reports `outside_allowed_changed=0` and `hotel_base_changed=0` for `S09`.
- Bridge-stair local raster attempts:
  `tasks/berlin-hotel-base/wave5_bridge_stairs_repair/results_v2/bridge_stairs_v2_board.png`
  were rejected as far from complete because they made a visible but crude local
  stair construction.
- User feedback on the wave6 OpenAI donor board: the top-right option was "near
  perfect".
- Accepted bridge-stair candidate:
  `tasks/berlin-hotel-base/wave6_bridge_stairs_openai_donor/results/stair_architecture_under_foliage_masked.png`.
- User feedback on the wave7 hotel-roof/right-side board: the top-right raw
  precise donor looked perfect, but the actual review had to verify that top
  floors were not distorted.
- Large context verification:
  `tasks/berlin-hotel-base/wave7_hotel_roof_facade_repair/results/hotel_roof_facade_right_side_floor_context_verification.txt`
  reports the raw precise donor changed `floor_guard_changed_vs_pre_roof=227064`
  and `stair_protected_changed_vs_pre_roof=631275`, while actual composites
  such as `v11_right_parapet_precise_reinforced.png` kept both guard counts at
  `0`.

## Procedure

1. Bank the current best full-resolution image first and never overwrite it.
2. Diagnose the actual defect before generating. Name whether it is an artifact,
   a missing structure, an occlusion problem, or a semantic continuity problem.
3. Draw explicit issue masks from the user's marks or from measured full-res
   boxes.
4. For semantic continuity plus occlusion, mask enough surrounding context for
   the model to see both the object and the occluder. A tiny patch can make the
   repair invisible or force a crude hand-drawn continuation.
5. Generate an external edit with OpenAI through
   `scripts/subgen.py --provider openai`, attaching the banked image and the
   mask.
6. Treat the external raw output as a donor only. It may return at a smaller
   size or repaint too much.
7. Resize/register the raw output back to baseline dimensions if needed.
8. Composite donor pixels back onto the banked baseline through a final blend
   mask with a feathered edge. This final mask may be smaller or differently
   shaped than the generation/context mask.
9. For repeated architecture, explicitly restore or protect the adjacent
   baseline structures that must not drift, such as floor grids, window columns,
   antenna shafts, or already-approved repair zones.
10. Verify changed pixels against the banked baseline, including a negative gate
   for protected regions that must remain unchanged.
11. Build a feedback board that includes conservative local repairs and the
   bounded external redraw, because the best visual result may be the broader
   donor even when it edits more pixels inside the allowed mask.
12. When the intended repair is subtle, include a marked crop or diff overlay so
    the reviewer can identify the actual change before any "fixed" claim.
13. When a crop does not show the preserved neighbor structures, build a larger
    context board before banking a result. A tight defect crop can hide that the
    donor warped a window/floor rhythm outside the crop.

## Failure Lessons

- Conservative local clone/inpaint variants were mechanically clean but could
  look blocky or smeared in watercolor haze; they are useful as safe baselines,
  not always the best final.
- Manual or procedural linework can be the wrong tool for semantic continuity
  repairs. The bridge-stair v1 was too subtle to see; v2 made stair bands
  visible but crude and incomplete. The successful lane prompted the model to
  redraw the stair-and-tree relationship as one local watercolor scene.
- Nano Banana produced a passing but visually broken bounded candidate in this
  lane due to square/raw-output seams and distorted tower structure.
- Photoshop connector was not reliable here because the tool returned HTTP 403.
- Direct image-generation outputs must not be accepted as final merely because
  they look good; the bounded composite and pixel verifier are the reliability
  layer.
- Do not describe a barely visible change as a fix. If the change cannot be
  identified on the review board, produce a clearer before/after crop or revise
  the method.
- Do not let a good-looking raw donor tile substitute for a safe composite. In
  the hotel-roof case, the raw donor looked best architecturally, but it also
  rewrote the top floors. The safe answer was a floor-guarded composite using
  the donor only where the roof/parapet needed reinforcement.

## Related

- [[concepts/svg-template-whole-redraw-from-roughs]]
- [[concepts/castle-panel-template-cut-bands]]
- [[index]]

## Open Questions

- Whether a future helper should automate mask-bounded donor compositing and
  verification for `scripts/subgen.py` edit outputs.
