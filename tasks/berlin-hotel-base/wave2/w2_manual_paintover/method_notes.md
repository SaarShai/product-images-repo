# w2_manual_paintover method notes

## Method

Deterministic local paintover, no remote/generative engine calls.

Inputs read:
- `tasks/berlin-hotel-base/HANDOFF.md`
- `tasks/berlin-hotel-base/BRIEF.md`
- `tasks/berlin-hotel-base/wave2/PLAN.md`
- `tasks/berlin-hotel-base/work/src.png`
- `tasks/berlin-hotel-base/work/tower_facade_above.png`
- `tasks/berlin-hotel-base/work/crop_base.png`
- `tasks/berlin-hotel-base/refs/ritz_cahill2.jpg`
- `tasks/berlin-hotel-base/refs/ritz_streetlevel.png`
- `tasks/berlin-hotel-base/RESULTS/M3_procedural_composited.png`

The script samples the artwork's own upper-tower stone/window colors and bay rhythm, uses the real refs only as architectural guidance for a quieter stone podium, and composites only inside the wave-2 box `3162,2582,4082,2845`.

## Recommendation

Recommended for judging: `w2_manual_e_soft_ref_hybrid_composited.png`.

Why: it keeps M3's seamless clone continuity at the upper seam, but replaces the repeated lower-floor feel with a softened, reference-informed stone base: regular vertical piers, small punched openings, low plinth, no canopy, no glass hall, no text. At full-scene scale it reads as a finished base without pulling attention from the skyline.

Conservative backup: `w2_manual_c_soft_podium_composited.png`.

## Candidate Visual Verdicts

- `w2_manual_a_clone_plinth_composited.png` - PASS mechanically, but too blocky/vector and has blank stone slabs; useful abandoned attempt, not recommended.
- `w2_manual_b_ref_piers_composited.png` - PASS mechanically, better base logic, but linework is too crisp/computer-clean; not recommended.
- `w2_manual_c_soft_podium_composited.png` - PASS mechanically, closest to M3 with a quieter low podium; good conservative backup, but still inherits some M3 repetition.
- `w2_manual_d_stronger_podium_composited.png` - PASS mechanically, hides more repetition, but the lower band risks reading slightly smoky/glassy.
- `w2_manual_e_soft_ref_hybrid_composited.png` - PASS mechanically, best balance of architecture, softness, and no-glass/no-canopy constraints; recommended pick.

## Attempts

1. Clone-plus-plinth from upper facade (`A`): proved region-only and preserved rhythm, but produced overly flat stone panels.
2. Fully hand-built ref-pier base (`B`): architecture improved, but the vector edge fought the watercolor source.
3. Soft podium over clone (`C`): restored source style and reduced glass-hall feel; kept too much M3 mechanical repetition.
4. Stronger podium over clone (`D`): more decisive base; lower openings looked a little too smoky at zoom.
5. Soft ref-pier hybrid (`E`): blended the hand-built pier/base architecture into the seamless clone baseline; selected.

## Assumptions

- The wave-2 default edit box `3162,2582,4082,2845` is the gate for this lane.
- Using M3 as a deterministic clone baseline is acceptable because M3 was built from the artwork's own upper tower; no new generated pixels were used here.
- Real refs informed architectural hierarchy only; no photo material was pasted into the artwork.
- Foreground tree/railing pixels inside the edit box should be preserved where practical, so the composite uses a soft foreground preservation mask.

## Verifier Output

Command:

```bash
python3 tasks/berlin-hotel-base/wave2/w2_manual_paintover/build_manual_paintover.py && for f in tasks/berlin-hotel-base/wave2/w2_manual_paintover/w2_manual_*_composited.png; do python3 tasks/berlin-hotel-base/wave2/verify_candidate.py --candidate "$f"; done
```

Output:

```text
PASS candidate=tasks/berlin-hotel-base/wave2/w2_manual_paintover/w2_manual_a_clone_plinth_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=620754
PASS candidate=tasks/berlin-hotel-base/wave2/w2_manual_paintover/w2_manual_b_ref_piers_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=622083
PASS candidate=tasks/berlin-hotel-base/wave2/w2_manual_paintover/w2_manual_c_soft_podium_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=613694
PASS candidate=tasks/berlin-hotel-base/wave2/w2_manual_paintover/w2_manual_d_stronger_podium_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=612092
PASS candidate=tasks/berlin-hotel-base/wave2/w2_manual_paintover/w2_manual_e_soft_ref_hybrid_composited.png box=3162,2582,4082,2845 outside_max=0 outside_nonzero=0 inside_nonzero=614817
```
