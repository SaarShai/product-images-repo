# Wave 2 Plan — Berlin Hotel Base Method Reset

## Goal

Produce a broad, comparable spread of new candidates for fixing the Ritz/Beisheim tower base in `tasks/berlin-hotel-base/work/src.png`, after wave 1 was rejected as not good enough. Prioritize method diversity and learnings over polishing one candidate.

## Scope

- Edit only the hotel base area unless a method intentionally generates a larger source plate that is then registered back into the base region.
- Never overwrite the Google Drive source image.
- Each method writes only under `tasks/berlin-hotel-base/wave2/<method-id>/`.
- Every candidate exported for review must be composited into full-res source dimensions and must pass the outside-region pixel gate.

## Methods

1. `w2_whole_tower` — generate or salvage a complete right-tower plate, then register/mask it into the artwork.
2. `w2_photo_rectified` — perspective-warp real Ritz base references into the target elevation, then art-convert/color-match.
3. `w2_vector_linework` — construct a clean vector/linework facade/base first, then texture/watercolorize.
4. `w2_photoshop_firefly` — use Photoshop/Firefly-style localized generative edit as a separate tool lane.
5. `w2_controlnet_comfy` — retry control-guided generation with a stronger hand-built structure/control map.
6. `w2_manual_paintover` — controlled clone/paintover from the artwork's own tower plus harmonization.
7. `w2_design_plates` — generate many standalone lower-tower/base plates, then register the best into the artwork.

## Shared Acceptance Gate

- Full-res candidate exists.
- Outside the allowed edit box, candidate must be byte-identical to `work/src.png`.
- Candidate must have a zoom crop and method note.
- The final review board must show all surviving candidates side by side with method labels.

## Allowed Edit Box

Default box is `x=3162..4082, y=2582..2845`. This covers the rejected base band while preserving the bridge, water, and untouched tower above. Methods may generate larger temporary plates, but their final composite must pass this box gate.

## Done Means

1. At least one candidate attempted for each method family above, or a method has a recorded blocker.
2. All successful candidates pass `python3 tasks/berlin-hotel-base/wave2/verify_candidate.py`.
3. A review board image exists in `tasks/berlin-hotel-base/wave2/results/`.
4. `SUMMARY.md` records method, files, gate result, and observed failure/success.
5. The user is shown the review board and asked for feedback.

