# Wave 3 Summary — TV Tower / Foreground Artifact Repair

## Baseline

- Full-res banked current best: `../wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png`
- User issue screenshot: `/Users/za/Desktop/Screenshot 2026-06-22 at 22.48.45.png`

## Initial Diagnosis

- The TV tower sphere has a semi-transparent crescent on its left edge that reads as a duplicate/ghost shape.
- The lower-left foreground has hard white vertical wipes and a fog band that reads more like an accidental erasure than watercolor atmosphere.
- The tower shaft/base and Brandenburg Gate overlap are partly washed out; repairs should clarify silhouettes without over-sharpening.

## Attempt Log

- `local_variants/` — 10 deterministic first-pass variants. All passed the broad pixel gate, but the foreground inpaint/tree-wash family looked too synthetic and blocky. Useful as a no-go: broad local repainting fixes metrics while hurting style.
- `refined_variants/` — 10 conservative variants. Stronger direction: reduce the sphere crescent and soften/tint only the worst lower foreground wipes.
- `agents/sphere_clean/` — 5 sphere-only worker variants. Best visual options are `sphere_clean_v03_watercolor_haze_blend.png` for painterly reduction and `sphere_clean_v05_strong_sky_haze_patch.png` for stronger removal.
- `agents/foreground_clean/` — 5 foreground-only worker variants. Best visual options are `foreground_clean_05_conservative_blend.png` for safest preservation, `foreground_clean_01_sampled_texture_patch.png` for stronger white-wipe reduction, and `foreground_clean_03_soft_watercolor_wash.png` for a softer atmospheric repair.
- `agents/external_edit_probe/` — OpenAI and Nano image-edit probes plus Photoshop attempt. OpenAI produced a mechanically valid but heavier bounded redraw; Nano produced a mechanically valid but visually broken result; Photoshop connector failed with HTTP 403.
- `shortlist/` — 9 combined full-res candidates, each repairing both sphere and foreground issue areas.

## Current Boards

- Feedback board: `results/wave3_feedback_board.png`
- Shortlist context board: `results/wave3_shortlist_board_context.png`
- Shortlist detail board: `results/wave3_shortlist_board_details.png`
- Refined local board: `results/wave3_refined_board_context.png`
- Rough learning board: `results/wave3_rough_learning_board_context.png`

## Verification

Fresh shortlist verification saved to `results/wave3_shortlist_verification.txt`.

Every shortlist candidate passes:

- `outside_allowed_changed=0`
- `hotel_base_changed=0`

The banked baseline remains untouched at `../wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png`.

## Shortlist Read

- `S01` / `S04` / `S08` are safest and most preserving.
- `S05` / `S06` remove more artifact but are more interventionist.
- `S09` is the broadest image-edit/redraw lane; it repairs the defects but changes the local character most.
