# w2_whole_tower method notes

## Pivot

New feedback said the standalone OpenAI p1/p2/p3 building plates look good and that the insertion is the real problem. I pivoted from generating more tower plates to registration/compositing experiments using the OpenAI plate pool.

`cand_openai_p1.png`, `cand_openai_p2.png`, and `cand_openai_p3.png` are byte-identical in this task folder (`shasum` matched), so the p123 variants use `cand_openai_p1.png` as the representative preferred source plate.

## Registration basis

- Source upper-facade period measured by vertical autocorrelation: about 90 px.
- OpenAI plate facade period measured by vertical autocorrelation: about 66 px.
- Rhythm scale used for p123 experiments: `90 / 66 = 1.3636`.
- Final composites edit only the verifier box `3162,2582,4082,2845`; temporary registered tower plates extend beyond that only as source material.

## Candidate set

- `w2_whole_tower_p123_rhythm_fullmask_composited.png`: actual OpenAI building bbox, rhythm scale, full allowed-box replacement with broad top/bottom feather.
- `w2_whole_tower_p123_rhythm_right_preserve_composited.png`: same rhythm registration, but fades the right side back to the original artwork so the receding side face is preserved. This is my recommended pick.
- `w2_whole_tower_p123_expanded_crop_occlusion_soft_composited.png`: expanded crop/lower anchor, softer seam, right-side preservation, and source-tree/foreground occlusion handling.

## Attempts abandoned

- Direct `codex exec` generation was stopped because the nested session began writing its own ledger outside the lane before producing an image; the stray nested ledger was removed.
- `generated_plate_openai_v2.png` was successfully produced through `scripts/subgen.py` and registered, but after the user pivot it is treated as a side attempt rather than the preferred lane output.
- Earlier registered `openai_p2_clean_masonry`, `flux2_p1_perspective`, and `openai_p2_lower_shaft_sample` attempts were too visibly rectangular/pasted or retained too much storefront/glass-hall character.

## Assumptions

- The wave2 default verifier box is the acceptance box even when the visual edit mostly targets the original base band.
- It is acceptable to preserve the original right side inside the allowed box when it improves perspective continuity.
- Since p1/p2/p3 are identical on disk, varying crop anchors, scale, masks, and compositing is the meaningful experiment axis.
