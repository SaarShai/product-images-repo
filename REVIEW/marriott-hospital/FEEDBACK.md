# Marriott Hospital — review + feedback

Full folder path: `/Users/za/Documents/product images repo/REVIEW/marriott-hospital/`

## CURRENT CANDIDATE: r12 (GEOMETRY V2 contract — first full round)

First round generated on the APPROVED master-template contract: door at the
orange anchor, center stabilizer-slot stripes kept feature-free, circle cutouts
complemented with the space-style painted bevel (navy inner shadow + lit lip),
stabilizer pair included. Route D two-stage (control+MRWC LoRA init →
ref-anchored named-palette restyle) + mask-cut.

Look at (in this folder):
1. `r12-screen-preview.jpg` — full screen: left + door + right + 2 stabilizers at template positions. **Main deliverable.**
2. `r12_left_final.png` — dusk courtyard; tree/bench/lamppost left, lit doorway right, slot lane quiet. IoU 0.9999, forbidden OK (0.93).
3. `r12_door_b_s1_final2.png` — named-palette door (stone facade, teal glass door, lanterns). IoU 1.0, forbidden OK (1.14).
4. `r12_door_b_s1_final.png` — first restyle of the same init (monochrome blue) — kept ONLY to show the anemia contrast; final2 is the candidate.
5. `r12_right_s2_final.png` — emergency wing: helipad H + windsock, shuttle at bay. IoU 0.9997, forbidden OK (1.27).
6. `r12_stab1_final.png` / `r12_stab2_final.png` — lantern-strip pair (same art registered, stab1 mirrored to its taper; finger holes read as lamp fixtures, beveled).
7. `r12-overlay-board.jpg` — red-cut overlays of the round-1 inits (geometry evidence).
8. `*_forb.png` — forbidden-stripe overlays per final.

## Questions for you
1. Door: teal GLASS door okay, or solid door (references lean solid)?
2. Door dome is darker navy than the narrows' dusk sky — harmonize, or keep as the center anchor?
3. Stabilizers: lantern-strip concept okay? (The model can't hold the 0.158 taper; registered-art route is deterministic.)
4. Anything on/near the center slot lanes that still bothers you?
5. Promote any of these toward production finals, or another round first?

## Process notes (what changed this round)
- forbidden_gate.py (new): caught tree-trunk-on-slot + shrubs-on-slots before spend; slot-edge exclusion added (control edges inside the stripe are legitimate).
- hole_bevel.py (new): space bevel now mask-driven; applied to every final.
- Anemia recurred on door restyle-1 → named-palette restyle fixed it (final2).
- Prompt-only feature placement is unreliable (5 left attempts) — codified as a finding; positional control via the control channel is the next tool if needed.

---
Earlier rounds kept in this folder for comparison: r9/r11 boards, style-options-board.jpg.
