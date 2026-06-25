# w2_photo_rectified method notes

## Inputs read

- `tasks/berlin-hotel-base/HANDOFF.md`
- `tasks/berlin-hotel-base/BRIEF.md`
- `tasks/berlin-hotel-base/wave2/PLAN.md`
- `tasks/berlin-hotel-base/work/src.png`
- `tasks/berlin-hotel-base/work/crop_base.png`
- `tasks/berlin-hotel-base/work/tower_facade_above.png`
- `tasks/berlin-hotel-base/refs/ritz_cahill2.jpg`
- `tasks/berlin-hotel-base/refs/ritz_streetlevel.png`

## Method

- Built deterministic candidates with `make_photo_rectified_candidates.py`.
- Rectified the two priority Ritz references with OpenCV homographies into the target edit-box aspect.
- Converted the rectified photo plates toward the source watercolor/ink palette by smoothing, desaturating, matching source crop color statistics, and applying restrained photo-derived edge linework.
- Composited only inside the requested full-source box `3162,2582,4082,2845`; everything outside that box remains byte-identical to `work/src.png`.
- Preserved a soft mask over the left-edge foliage overlap so the tree does not get fully overwritten.

## Homography source quads

- `ritz_cahill2.jpg`: `[(92,423), (508,423), (512,646), (86,650)]`.
- `ritz_streetlevel.png`: `[(77,244), (548,252), (585,536), (49,528)]`.

Diagnostic overlays are saved as `_quad_cahill2.png` and `_quad_streetlevel.png`.

## Candidates

- `w2_photo_rectified_simplified_strong_composited.png` - recommended pick for this lane. It uses the rectified photo plates for texture and detail, then snaps the bay/window rhythm to the target artwork. It reads more like a continued stone facade and avoids canopy/text. Residual risk: visibly constructed/flat at zoom level and not as seamless as a true hand paintover.
- `w2_photo_rectified_simplified_composited.png` - softer version of the recommended plate. Better translucency at seams, but the original broken glass band bleeds through more.
- `w2_photo_rectified_hybrid_composited.png` - blend of direct Cahill2 and street-level watercolor plates. Passes containment, but looks murky and still inherits too much distorted photo structure.
- `w2_photo_rectified_streetlevel_composited.png` - direct street-level rectification. Passes containment, but still feels slanted/photo-derived and too dense.
- `w2_photo_rectified_cahill2_composited.png` - direct Cahill2 rectification. Passes containment, but carries unwanted side/canopy/station geometry and reads pasted.

## Attempts and outcomes

- Direct Cahill2 warp: successful technically, rejected visually because the selected real crop includes side/station geometry and many compressed upper-floor windows.
- Direct street-level warp: successful technically, rejected visually because one broad homography could not fully remove the camera perspective across mixed planes.
- Hybrid direct warp: reduced single-reference artifacts but remained too murky and glassy.
- Simplified aligned plate: used the rectified photos as source texture/line evidence but rebuilt the visible facade in the target elevation rhythm. This became the lane recommendation.

## Assumptions

- The allowed wave-2 edit box is `3162,2582,4082,2845`, per the worker prompt and `wave2/PLAN.md`.
- It is acceptable for this lane to provide a method candidate rather than a final seamless production winner, because the fleet judge will compare method families.
- No Google Drive files were written.
- All generated files were written under `tasks/berlin-hotel-base/wave2/w2_photo_rectified/`.

## Verifier

Command:

```bash
for f in tasks/berlin-hotel-base/wave2/w2_photo_rectified/w2_photo_rectified_*_composited.png; do python3 tasks/berlin-hotel-base/wave2/verify_candidate.py --candidate "$f" --box 3162,2582,4082,2845; done
```

Output:

```text
PASS candidate=tasks/berlin-hotel-base/wave2/w2_photo_rectified/w2_photo_rectified_cahill2_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=717913
PASS candidate=tasks/berlin-hotel-base/wave2/w2_photo_rectified/w2_photo_rectified_hybrid_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=718075
PASS candidate=tasks/berlin-hotel-base/wave2/w2_photo_rectified/w2_photo_rectified_simplified_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=717991
PASS candidate=tasks/berlin-hotel-base/wave2/w2_photo_rectified/w2_photo_rectified_simplified_strong_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=718589
PASS candidate=tasks/berlin-hotel-base/wave2/w2_photo_rectified/w2_photo_rectified_streetlevel_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=718583
```
