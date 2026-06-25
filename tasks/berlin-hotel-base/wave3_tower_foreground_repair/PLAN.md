# Wave 3 Plan — TV Tower / Foreground Artifact Repair

## Goal

Produce several comparable repair candidates for the green-circled defects in `/Users/za/Desktop/Screenshot 2026-06-22 at 22.48.45.png`, starting from the banked current best:

`tasks/berlin-hotel-base/wave2/BANKED_CURRENT_BEST/berlin_hotel_base_current_best.png`

## Defects To Address

1. TV tower sphere left-side ghost crescent / duplicate shadow.
2. Hard white vertical wipes and fogged-out foreground at the left of the tower.
3. Hazy, partially erased tower-base / Brandenburg Gate overlap.

## Scope

- Preserve the banked current best exactly; all outputs go under this `wave3_tower_foreground_repair/` folder.
- Edit only the far-left tower / Brandenburg foreground context unless a method explicitly writes a larger candidate for comparison and labels it honestly.
- Keep the Berlin hotel/base fix from wave2 unchanged.
- Produce a board with method labels and zoom crops for feedback.

## Method Lanes

1. `local_clean` — deterministic local watercolor cleanup: remove the sphere crescent and soften obvious white wipes while preserving the tower.
2. `clone_sky_tree` — patch defects using nearby sky/tree/column texture, then harmonize with blur/grain/watercolor softness.
3. `haze_reduce` — reduce lower fog and recover foreground silhouettes without making the scene too crisp.
4. `image_edit_prompt` — attempt a bounded image-generation/edit lane if an available local subscription route can use the banked image and masks.
5. `hybrid_combo` — combine the least invasive successful elements from the earlier lanes.

## Done Means

1. At least 8 full-res variants exist, or blockers are recorded for unavailable external tools.
2. Each variant has a zoom crop of the issue area.
3. A review board exists showing the baseline plus variants.
4. A verification report records each variant's changed bounding box and whether it leaves the hotel-base edit region untouched.
5. The user receives paths to the board and the strongest candidate set for feedback.
