# r16 eval rubric — derived from marriott-hospital.style-spec.yaml (v1)

Score each 0-5. SHIP GATE: medium_finish ≥4 AND no criterion ≤1 AND geometry PASS.
Every failure becomes a spec patch + a permanent case here.

| # | criterion | 5 looks like | 0 looks like |
|---|-----------|--------------|--------------|
| 1 | medium_finish | matte hand-painted watercolor, paper grain, soft diffuse light | glossy 3D-toy plastic OR felt fiber |
| 2 | palette_poles | named colors present; BOTH warm (cream/gold) and cool (cobalt/teal) poles | anemic monochrome / single pole |
| 3 | architecture | chunky rounded storybook civic building (police/fire cartoon family) | realistic render or flat modern box |
| 4 | cross_count_shape | exactly ONE rounded-square badge w/ white cross (canopy mini optional) | multiple mismatched crosses / crucifix shapes |
| 5 | detail_density | storybook-medium: props around entry, no empty walls, readable | empty anemic walls OR clutter |
| 6 | motifs | playful details present (siren light, teddy, planters) integrated | missing or sticker-like |
| 7 | signage | all plaques/signs blank | any painted letters/logos |
| 8 | geometry | door fills anchor arch, slot lanes quiet, IoU ≥0.95, holes clear | drifted arch / features on slots |

## r16_door_final scores (2026-07-05, Fable vision + gates)
1 medium_finish **5** (true matte watercolor, grain) · 2 palette_poles **5** ·
3 architecture **5** (police-family dome+canopy+sconces) · 4 cross **5** (exactly ONE round badge) ·
5 density **5** (toy-filled windows, no empty walls) · 6 motifs **3.5** (teddy ✓; SIREN dropped by model despite prompt) ·
7 signage **4** (notes carry dash-squiggles, not letters — verified hi-DPI; one 7-ish pot mark) · 8 geometry **5** (IoU 1.0, forbidden OK 1.13).
GATE: **PASS** → shipped. Case learned: required props need a per-prop presence CHECK, not just prompt inclusion.

## r16b_door_final scores (post user-patch round)
1 medium **5** · 2 poles **5** (white walls + warm window glow + cobalt) · 3 architecture **5** ·
4 cross **5 after LaMa fix** (correct blue rounded-square/white; restyle had ADDED a duplicate round cross — new case: restyle can INSERT extra emblems, count-check must run POST-restyle) ·
5 density **5** (toy arch) · 6 motifs **4** (teddy ✓ siren nub small) · 7 signage **5** · 8 geometry **4.5** (fill-IoU 0.9322, forbidden OK).
GATE: PASS. User corrections applied: no awning ✓, hospital-white ✓, badge form ✓.
