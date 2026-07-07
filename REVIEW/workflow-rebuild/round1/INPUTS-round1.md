# INPUTS — round1

Full labeled board: [INPUTS-round1.jpg](INPUTS-round1.jpg)

## Reference images (from `handle/style-handle.yaml`)

| role | file | provenance | used by |
|---|---|---|---|
| medium_ref | 01-medium_ref.jpg | bible-v1 refs_by_role.medium_anchor -> medium_ref (brief role map); harvested flat-art crop of collection's own original source art, not a generated DOOR round | arm-g_prompt.md (Image 2), arm-l_prompt.md (Image 2) |
| feature_ref | 02-feature_ref.png | bible-v1 refs_by_role.medium_anchor supplementary crop; demoted to feature_ref since build_style_handle.py allows exactly one medium_ref file (Kitchen screen fine-line technique diversity) | supplementary (not directly numbered in either prompt) |
| feature_ref | 03-feature_ref-02.png | bible-v1 refs_by_role.medium_anchor supplementary crop; demoted to feature_ref (Water Cube technique diversity) | supplementary |
| palette_ref | 04-palette_ref.png | bible-v1 refs_by_role.palette -> palette_ref (brief role map); Hospital-screen facade crop, same-screen palette truth | arm-g_prompt.md (Image 3), arm-l_prompt.md (Image 3) |
| feature_ref | 05-feature_ref-03.png | bible-v1 refs_by_role.palette supplementary crop; demoted to feature_ref (Hospital-screen garden crop, warm/cool pole coverage) | supplementary |
| style_ref | 06-style_ref.png | bible-v1 refs_by_role.architecture_anchor -> style_ref (brief role map, naming mismatch is known); shape language + composition anchor; harvested photo, not a generated DOOR round | arm-g_prompt.md (Image 4), arm-l_prompt.md (Image 4) |
| feature_ref | 07-feature_ref-04.png | bible-v1 refs_by_role.architecture_anchor supplementary; demoted to feature_ref since build_style_handle.py allows exactly one style_ref file; playful civic-building composition and detail style | supplementary |

## Guides

| file | used by |
|---|---|
| guides/arm-g_geometry-only.png | arm-g_prompt.md (Image 1 — plain grey silhouette, no feature zones) |
| guides/arm-l_layout-human.png | arm-l_prompt.md (Image 1 — silhouette + grey placement zones per required feature) |
| guides/arm-l_layout-model.png | arm-l arm variant / model-facing layout guide |

## Prompts

| prompt file | arm |
|---|---|
| prompts/arm-g_prompt.md | arm-g (geometry-only guide arm) |
| prompts/arm-l_prompt.md | arm-l (layout-zoned guide arm) |
