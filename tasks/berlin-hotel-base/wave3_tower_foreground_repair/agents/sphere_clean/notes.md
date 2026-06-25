# Sphere Clean Repair Notes

Baseline: `tasks/berlin-hotel-base/wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png`

Assigned edit box: `x=190..470 y=1120..1580`

Required zoom crop: `x=120..520 y=1040..1660`

## Methods And Files

1. `sphere_clean_v01_sky_texture_patch.png`
   - Method: low-opacity shifted clean-sky texture patch, applied through a curved crescent mask.
   - Crop: `sphere_clean_v01_sky_texture_patch_zoom_x120-520_y1040-1660.png`
   - What worked: reduces the left duplicate crescent without touching the sphere band or tower shaft.
   - What failed / caveat: faint crescent structure remains; patch is intentionally conservative.

2. `sphere_clean_v02_subtle_mirror_sky.png`
   - Method: subtle crop mirroring from the clean sky left of the artifact.
   - Crop: `sphere_clean_v02_subtle_mirror_sky_zoom_x120-520_y1040-1660.png`
   - What worked: smallest medium-strength sky replacement, with less intrusion toward the true sphere edge.
   - What failed / caveat: still leaves a visible pale ghost edge in the lower crescent.

3. `sphere_clean_v03_watercolor_haze_blend.png`
   - Method: watercolor haze blend using shifted sky plus a blurred sky wash.
   - Crop: `sphere_clean_v03_watercolor_haze_blend_zoom_x120-520_y1040-1660.png`
   - What worked: softens the ghost while keeping the image painterly and low contrast.
   - What failed / caveat: more reduction than removal; best if the judge prefers atmospheric continuity.

4. `sphere_clean_v04_edge_soft_mask.png`
   - Method: edge-only mask with local inpaint, limited to detected crescent linework.
   - Crop: `sphere_clean_v04_edge_soft_mask_zoom_x120-520_y1040-1660.png`
   - What worked: least invasive candidate; touches only 1,203 pixels and preserves nearly all original texture.
   - What failed / caveat: only reduces the darkest lower crescent edges; the broad ghost remains.

5. `sphere_clean_v05_strong_sky_haze_patch.png`
   - Method: stronger clean-sky patch with haze-softened curved edges.
   - Crop: `sphere_clean_v05_strong_sky_haze_patch_zoom_x120-520_y1040-1660.png`
   - What worked: strongest ghost reduction in this set without pulling dark tower colors into the patch.
   - What failed / caveat: most likely to read as a local sky repaint under close inspection.

Supporting files:
- `make_sphere_clean_variants.py` - deterministic generator used for the variants.
- `baseline_zoom_x120-520_y1040-1660.png` - baseline comparison crop.
- `sphere_clean_contact_sheet.png` - baseline plus five candidate crops.
- `mask_sphere_ghost_broad.png`, `mask_sphere_ghost_narrow.png`, `mask_sphere_ghost_edges.png` - generated masks used by the repair lanes.

## Official Verifier Output

Command:

```bash
for candidate in tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v01_sky_texture_patch.png tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v02_subtle_mirror_sky.png tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v03_watercolor_haze_blend.png tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v04_edge_soft_mask.png tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v05_strong_sky_haze_patch.png; do python3 tasks/berlin-hotel-base/wave3_tower_foreground_repair/verify_wave3.py --candidate "$candidate"; done
```

Output:

```text
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v01_sky_texture_patch.png bbox=(201, 1186, 293, 1539) max_delta=58 inside_allowed_changed=20747 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v02_subtle_mirror_sky.png bbox=(201, 1187, 274, 1536) max_delta=47 inside_allowed_changed=18180 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v03_watercolor_haze_blend.png bbox=(201, 1187, 293, 1539) max_delta=34 inside_allowed_changed=20334 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v04_edge_soft_mask.png bbox=(213, 1356, 262, 1495) max_delta=37 inside_allowed_changed=1203 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
PASS candidate=tasks/berlin-hotel-base/wave3_tower_foreground_repair/agents/sphere_clean/sphere_clean_v05_strong_sky_haze_patch.png bbox=(200, 1185, 294, 1539) max_delta=74 inside_allowed_changed=21607 outside_allowed_changed=0 hotel_base_changed=0 allowed_box=(0, 900, 860, 3050) hotel_base_box=(3162, 2582, 4082, 2845)
```

## Tight Assigned-Region Byte Check

The official verifier allows a broader tower/foreground box, so I also checked that every changed pixel stays inside the assigned sphere region.

```text
TIGHT sphere_clean_v01_sky_texture_patch.png bbox=(201, 1186, 293, 1539) outside_assigned_changed=0 changed=20747 edit_box=(190, 1120, 470, 1580)
TIGHT sphere_clean_v02_subtle_mirror_sky.png bbox=(201, 1187, 274, 1536) outside_assigned_changed=0 changed=18180 edit_box=(190, 1120, 470, 1580)
TIGHT sphere_clean_v03_watercolor_haze_blend.png bbox=(201, 1187, 293, 1539) outside_assigned_changed=0 changed=20334 edit_box=(190, 1120, 470, 1580)
TIGHT sphere_clean_v04_edge_soft_mask.png bbox=(213, 1356, 262, 1495) outside_assigned_changed=0 changed=1203 edit_box=(190, 1120, 470, 1580)
TIGHT sphere_clean_v05_strong_sky_haze_patch.png bbox=(200, 1185, 294, 1539) outside_assigned_changed=0 changed=21607 edit_box=(190, 1120, 470, 1580)
```

## Dimension Check

```text
sphere_clean_v01_sky_texture_patch.png (4192, 3848)
sphere_clean_v01_sky_texture_patch_zoom_x120-520_y1040-1660.png (400, 620)
sphere_clean_v02_subtle_mirror_sky.png (4192, 3848)
sphere_clean_v02_subtle_mirror_sky_zoom_x120-520_y1040-1660.png (400, 620)
sphere_clean_v03_watercolor_haze_blend.png (4192, 3848)
sphere_clean_v03_watercolor_haze_blend_zoom_x120-520_y1040-1660.png (400, 620)
sphere_clean_v04_edge_soft_mask.png (4192, 3848)
sphere_clean_v04_edge_soft_mask_zoom_x120-520_y1040-1660.png (400, 620)
sphere_clean_v05_strong_sky_haze_patch.png (4192, 3848)
sphere_clean_v05_strong_sky_haze_patch_zoom_x120-520_y1040-1660.png (400, 620)
```
