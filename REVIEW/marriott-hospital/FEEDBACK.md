# Marriott Hospital — review + feedback

Full folder path: `/Users/za/Documents/product images repo/REVIEW/marriott-hospital/`

## CURRENT CANDIDATE: r13 (your 3 corrections applied)

Your turn-66 feedback → this round:
1. **No dashed lines in geometry refs** — fixed at the source (master_spec.py):
   dashed guide strokes filtered, dome closure smoothed, door anchor drawn as a
   synthetic SOLID arch. Dash marks gone from the finals' dome tops.
2. **Door details, police/fire spirit** — detail vocabulary mined from the
   Police/Fire originals (cupola, shield badge, canopy downlights, framed arched
   windows, notice board, sconces, ceramic planters) and adapted to hospital.
3. **Narrows = independent buildings** — both narrows are now complete building
   facades (left: garden wing; right: tower with ambulance bay + red cross shield),
   center slot lanes on plain pilaster/wall strips.

Look at (in this folder):
1. `r13-screen-preview.jpg` — full screen. **Main deliverable.**
2. `r13_left_final.png` — garden-wing facade. Fill-IoU 0.9999, forbidden OK (0.94).
3. `r13_door_final.png` — detail-rich entrance (striped awning dome, cross roundels, canopy, sconce clusters, hedges, blank plaque). Fill-IoU 1.0, forbidden OK (1.10).
4. `r13_right_final.png` — emergency tower, ambulance in warm-lit bay. Fill-IoU 1.0, forbidden OK (1.16).
5. `r13-overlay-board.jpg` — all 6 round-1 candidates with cut+forbidden overlays.
6. `*_forb.png` — forbidden-lane overlays per final.

FIXED since first r13 post: door-leaf crosses are now clean equal-arm medical
crosses (was thin crucifix). Hand-compositing seamed on the gradient glass; the
working fix was Flux Fill masked-inpaint on a tight two-cross mask — integrates
into the watercolor with no halo/seam. `r13_door_final.png` is the fixed door.

ALSO NEW: stabilizers now MATCH the building look — narrow cream-stone pilaster
strips with round windows, a wall lantern, blue tiled cap, hedges (was r12's
hanging-lantern strips). `r13_stab1/2_final.png`. r12 lantern strips still on
file if you prefer those.

## Questions
- r13 door detail level right now, or push denser?
- Narrows as buildings: does this match the cap-juluca/space/princess intent?
- Stabilizers: building-pilaster (r13) or lantern-strip (r12)?
- Door emblems: the two leaf crosses are painted — keep painted, or make them a
  VECTOR layer in the .ai like signage (crisper, editable)?

---

## PREVIOUS: r12 (GEOMETRY V2 contract — first full round)

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
