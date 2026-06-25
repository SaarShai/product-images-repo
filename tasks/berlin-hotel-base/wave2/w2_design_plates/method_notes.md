# w2_design_plates Method Notes

## Goal

Generate or assemble standalone lower-tower/base design plates, choose the strongest 1-3, and register them into `tasks/berlin-hotel-base/work/src.png` without changing pixels outside the wave-2 box `3162,2582,4082,2845`.

## Outputs

- Plate survey: `plate_sheet.png`
- Ranked registered candidates: `ranked_candidates_sheet.png`
- Earlier selected sheet: `selected_candidates_sheet.png`
- Zoom sheet: `candidate_zooms_sheet.png`
- Plate manifest: `manifest.tsv`
- Generator/assembler: `make_design_plates.py`
- Verifier transcript: `verifier_output.txt`

## Standalone Plate Attempts

Generated 15 standalone 920x263 plates under `plates/`:

- `plate_01_source_continue_clean.png`
- `plate_02_source_continue_lowerrow.png`
- `plate_03_source_continue_grounded.png`
- `plate_04_source_continue_tall.png`
- `plate_05_openai_p1_lowerbase.png`
- `plate_06_openai_p2_lowerbase.png`
- `plate_07_openai_p3_lowerbase.png`
- `plate_08_frontal_wc_lowerbase.png`
- `plate_09_flux2_p1_lowerbase.png`
- `plate_10_flux2_p3_lowerbase.png`
- `plate_11_streetlevel_watercolorized.png`
- `plate_12_hybrid_source_openai_p1.png`
- `plate_13_hybrid_source_openai_p2.png`
- `plate_14_hybrid_source_frontal_wc.png`
- `plate_15_hybrid_source_streetlevel.png`

## Promoted Candidates

Rank 1: `composites/final_rank1_source_continue_grounded_composited.png`

- Source plate: `plates/plate_03_source_continue_grounded.png`
- Visual verdict: safest and most seamless. It continues the existing limestone/window rhythm down to the quay and removes the glass-hall/canopy read. Risk: conservative/repetitive; it is more continuation than newly designed entrance character.

Rank 2: `composites/final_rank2_hybrid_source_openai_p1_composited.png`

- Source plate: `plates/plate_12_hybrid_source_openai_p1.png`
- Visual verdict: adds the clearest designed lower-base block from the standalone OpenAI tower plate while keeping artwork-native facade context. Risk: the central base feels a little blunt/blocky under the existing tower rhythm.

Rank 3: `composites/final_rank3_hybrid_source_frontal_wc_composited.png`

- Source plate: `plates/plate_14_hybrid_source_frontal_wc.png`
- Visual verdict: quieter than rank 2 and less glassy than the source. Risk: lower horizontal stripe is busy and the right side reads less resolved than rank 1.

All promoted composites preserve foreground tree/branch pixels inside the allowed box with a soft color mask to avoid a hard tree cutoff at x=3162.

## Attempts Tried And Abandoned

- Pure standalone OpenAI lower-base extracts (`plate_05`-`plate_07`): useful masonry base vocabulary, but unregistered tower width created a pasted central block unless blended with the source facade.
- Flux2 standalone extracts (`plate_09`, `plate_10`): interesting watercolor texture, but 3/4/photo perspective and podium shapes do not match the flat source elevation.
- Street-level reference conversion (`plate_11`, `plate_15`): carries real base information, but the photo perspective and faint hotel text are disqualifying risks for this artwork.
- First hybrid pass: blank paper margins from standalone plates pasted into the base. Fixed by using the artwork-native facade as a fallback and alpha-applying only real darker building detail from extracted plates.
- Subscription generation was not invoked in this lane. Existing standalone image-generation outputs plus the artwork's own facade were sufficient to assemble a broad plate spread, and the brief allowed either generate or assemble.

## Assumptions

- The allowed edit box is the wave-2 default: `3162,2582,4082,2845`.
- Writing is confined to `tasks/berlin-hotel-base/wave2/w2_design_plates/`.
- The Google Drive source remains read-only and untouched.
- Source-derived plates count as assembled design plates because this lane's goal allows generate or assemble.
- The foreground tree can be preserved from the current source inside the edit box because it is foreground context, not part of the hotel-base design.

## Learnings

- The strongest visual plate was still artwork-native: copying the source facade rhythm downward with a controlled plinth best matched scale, style, and right-side perspective.
- Standalone generated towers are most useful as base-detail donors, not as full-width plates; they need source-facade fallback outside their registered detail area.
- Real street-level references are dangerous without a stronger rectification/art-conversion pass because they carry text, flags, street perspective, and photographic contrast.
- The plate-sheet step caught blank-margin failures before verification; the verifier only proves region containment, not visual suitability.

## Verifier Output

```text
PASS candidate=tasks/berlin-hotel-base/wave2/w2_design_plates/composites/final_rank1_source_continue_grounded_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=636932
PASS candidate=tasks/berlin-hotel-base/wave2/w2_design_plates/composites/final_rank2_hybrid_source_openai_p1_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=636041
PASS candidate=tasks/berlin-hotel-base/wave2/w2_design_plates/composites/final_rank3_hybrid_source_frontal_wc_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=636768
```
