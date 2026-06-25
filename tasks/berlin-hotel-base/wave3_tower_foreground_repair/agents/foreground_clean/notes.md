# Foreground Clean Repair Notes

Baseline:
`tasks/berlin-hotel-base/wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png`

Assigned edit region:
`x=0..620, y=2050..2920`

Required zoom crop:
`x=0..760, y=1960..3040`

## Method Summary

Generated five local full-resolution repair candidates. Each candidate starts
from the banked baseline and writes modified pixels only inside the assigned
lower-left foreground edit region. The final generation script enforces this by
copying the baseline full-res image and replacing only `EDIT_BOX =
(0, 2050, 620, 2920)`.

The final pass avoided broad inpainting because it created visible wedge/blob
artifacts. The accepted pass uses narrower local methods:

- `foreground_clean_01_sampled_texture_patch.png`
  - Method: horizontal same-row texture interpolation across narrow vertical
    wipe strips, plus subtle local haze toning.
  - Worked: strongest reduction of the white pole/wipe artifacts without broad
    shapes or edge seams.
  - Failed/risk: still leaves a softened pale vertical read in places because
    adjacent source texture is also hazy.

- `foreground_clean_02_haze_thinning.png`
  - Method: local value reduction, saturation recovery, and gentle contrast on
    the fog band.
  - Worked: least invented texture; reduces flat fog slightly.
  - Failed/risk: hard vertical wipe traces remain more visible.

- `foreground_clean_03_soft_watercolor_wash.png`
  - Method: horizontal wipe patching blended with bilateral watercolor
    softening and very light tonal adjustment.
  - Worked: softer atmospheric version; avoids the earlier hard paint blocks.
  - Failed/risk: lower structural recovery; some pale bands remain.

- `foreground_clean_04_tree_silhouette_restoration.png`
  - Method: sampled texture patching plus faint restored branch/trunk/leaf
    silhouettes in the wiped tree area.
  - Worked: gives the erased tree area more intentional foreground structure.
  - Failed/risk: most assertive/stylized option; restored marks should be judged
    visually for whether they feel native to the watercolor style.

- `foreground_clean_05_conservative_blend.png`
  - Method: low-alpha blend of sampled texture repair and haze thinning.
  - Worked: safest preservation candidate.
  - Failed/risk: weakest artifact reduction; best if minimal intervention is
    preferred.

## Files

- Full-res candidate: `foreground_clean_01_sampled_texture_patch.png`
- Zoom crop: `foreground_clean_01_sampled_texture_patch_zoom_x0-760_y1960-3040.png`
- Full-res candidate: `foreground_clean_02_haze_thinning.png`
- Zoom crop: `foreground_clean_02_haze_thinning_zoom_x0-760_y1960-3040.png`
- Full-res candidate: `foreground_clean_03_soft_watercolor_wash.png`
- Zoom crop: `foreground_clean_03_soft_watercolor_wash_zoom_x0-760_y1960-3040.png`
- Full-res candidate: `foreground_clean_04_tree_silhouette_restoration.png`
- Zoom crop: `foreground_clean_04_tree_silhouette_restoration_zoom_x0-760_y1960-3040.png`
- Full-res candidate: `foreground_clean_05_conservative_blend.png`
- Zoom crop: `foreground_clean_05_conservative_blend_zoom_x0-760_y1960-3040.png`
- Contact sheet: `candidate_crops_contact_sheet.png`
- Baseline crop reference: `baseline_zoom_reference.png`
- Assigned-region reference crop: `assigned_region_reference.png`
- Generation script: `make_foreground_clean_variants.py`
- Manifest: `generated_manifest.txt`

## Verifier Output

Command form:

```bash
python3 tasks/berlin-hotel-base/wave3_tower_foreground_repair/verify_wave3.py --candidate <candidate>
```

Output:

```text
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/foreground_clean/foreground_clean_01_sampled_texture_patch.png bbox=(0, 2106, 619, 2798) max_delta=92 inside_allowed_changed=325985 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/foreground_clean/foreground_clean_02_haze_thinning.png bbox=(0, 2111, 619, 2798) max_delta=16 inside_allowed_changed=419754 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/foreground_clean/foreground_clean_03_soft_watercolor_wash.png bbox=(0, 2106, 619, 2798) max_delta=49 inside_allowed_changed=327960 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/foreground_clean/foreground_clean_04_tree_silhouette_restoration.png bbox=(0, 2106, 619, 2798) max_delta=92 inside_allowed_changed=338301 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/foreground_clean/foreground_clean_05_conservative_blend.png bbox=(0, 2106, 619, 2798) max_delta=15 inside_allowed_changed=409353 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
```

## Assigned-Region Byte Check

Additional stricter comparison against the exact assigned edit box:

```text
foreground_clean_01_sampled_texture_patch.png: outside_assigned_changed=0 inside_assigned_changed=325985 bbox=(0, 2106, 619, 2798)
foreground_clean_02_haze_thinning.png: outside_assigned_changed=0 inside_assigned_changed=419754 bbox=(0, 2111, 619, 2798)
foreground_clean_03_soft_watercolor_wash.png: outside_assigned_changed=0 inside_assigned_changed=327960 bbox=(0, 2106, 619, 2798)
foreground_clean_04_tree_silhouette_restoration.png: outside_assigned_changed=0 inside_assigned_changed=338301 bbox=(0, 2106, 619, 2798)
foreground_clean_05_conservative_blend.png: outside_assigned_changed=0 inside_assigned_changed=409353 bbox=(0, 2106, 619, 2798)
```

All candidates preserve pixels byte-identical outside `x=0..620,
y=2050..2920`; the provided verifier also reports `hotel_base_changed=0` for
all candidates.
