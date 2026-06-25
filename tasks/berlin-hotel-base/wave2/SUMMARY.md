# Wave 2 Summary — Berlin Hotel Base

Status: setup in progress.

## Attempts

- `w2_verifier_board`: main thread created `w2_verifier_board/build_board.py`; smoke test output `scanned=0 pass=0`. This will aggregate full-res candidate PNGs after method lanes return.
- `w2_photoshop_firefly`: blocked before generation. Adobe Photoshop connector returned `403 Forbidden` on `_instructedit`; see `w2_photoshop_firefly/method_notes.md`.
- `w2_main_tower_plate`: generated `frontal_elevation_base_registered.png` from existing full-tower watercolor elevation. Board verifier: PASS, outside delta 0.
- `w2_main_design_plate`: generated `openai_p1_lower_base_registered.png` from unjudged OpenAI whole-tower plate. Board verifier: PASS, outside delta 0.
- `w2_main_photo_stylized`: generated `streetlevel_facade_artified.png` from real street-level reference crop. Board verifier: PASS, outside delta 0.
- `w2_main_vector_paintover`: generated `vector_pier_window_base.png` from deterministic linework/paintover. Board verifier: PASS, outside delta 0.
- `w2_whole_tower`: worker returned p123-focused OpenAI plate registration after user feedback. Best base-only candidate: `w2_whole_tower_p123_rhythm_right_preserve_composited.png`; default edit-box verifier PASS, outside delta 0.
- `w2_photo_rectified`: worker returned five rectified/photo-derived candidates. Best per worker: `w2_photo_rectified_simplified_strong_composited.png`; default edit-box verifier PASS, outside delta 0. Visually still somewhat constructed/photo-derived.
- `w2_vector_linework`: worker returned v1/v2/v3. Best per worker: `w2_vector_linework_v3_composited.png`; default edit-box verifier PASS, outside delta 0. Visually more synthetic than OpenAI plate lanes.
- `w2_manual_paintover`: worker returned five deterministic paintover candidates. Best per worker: `w2_manual_e_soft_ref_hybrid_composited.png`; default edit-box verifier PASS, outside delta 0.
- `w2_controlnet_comfy`: Comfy server unavailable (`127.0.0.1:8188` connection refused); fallback SD1.5 lineart ControlNet produced two passing candidates, but both are visibly stiff/gridded.
- `w2_design_plates`: worker generated/assembled 15 plates and promoted three. User feedback afterward: standalone OpenAI p1/p2/p3 building plates look great; insertion into the composite is the hard part.
- `w2_openai_integration`: main-thread detail-transfer attempts using OpenAI p1 as donor passed the default edit-box gate, but looked ghosted because the tight band preserved too much old base haze.
- `w2_openai_large_insert`: large masked insertion of OpenAI p1/p2/p3 lets the building source breathe, but changes much more of the tower and loses some original perspective. Verified with actual large box, not default base box.
- `w2_openai_model_integration`: subscription OpenAI edit produced donor images; final promoted file `openai_reference_integrated.png` (v4) is the strongest finished-base look but uses a broader measured box `(2956,2480,4192,3060)`. It passes that measured-box verifier, but fails the default base-only board by design.

## Current Synthesis

User correction after the focused board: the best integrations are the subtle `w2_openai_integration` variants, not the broader model-donor/full-plate composites. The current baseline folder is:

- `USER_SELECTED_openai_subtle_integrations/`

Selected candidates:

- `openai_p1_centered_front_face.png`
- `openai_p1_detail_transfer_soft.png`
- `openai_p1_floor_rhythm_crop.png`
- `openai_p1_groundfloor_only.png`

All four pass the original base-only verifier with `box=3162,2582,4082,2845`, `outside_max=0`, `outside_nonzero=0`.

Revised learning: OpenAI standalone p1/p2/p3 are strong architectural sources, but the successful integration route is subtle detail transfer into the existing painting, not a stronger/full replacement. Broader model-donor composites look more finished in isolation but integrate worse.
