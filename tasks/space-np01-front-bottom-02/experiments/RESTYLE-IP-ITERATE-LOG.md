# RESTYLE IP-Adapter Iterate Log (LOCAL-DIFFUSERS route, Apple MPS)

Goal: does a higher IP-Adapter scale pull the local lineart-CN renders toward the
BRIGHT COLORFUL reference (cobalt panel, red/green/gold capsule buttons, cream knob
with radial ticks, colorful sliders, gold/red tick column, white bg)?

Recipe: `scripts/controlnet_style_gen.py` — lineart ControlNet (control_v11p_sd15_lineart)
locks contour+openings; IP-Adapter injects style from the 2 reference PNGs; base = dreamshaper-8.
Control map = cn-lineart-480.png (480x1624). ~11 min/gen on MPS.

Reference target features (STYLE-RUBRIC.md): bright mid-cobalt rounded-rect panel /
RED+GREEN+GOLD capsule buttons / cream knob w/ radial ticks / colorful sliders+dots /
gold+red tick column / white granulated bg. Gate: style>=4 AND brightness AND colorful controls.

| Round | Dir | ip-scale | cond-scale | steps | prompt note | geom (IoU) | style /5 | what changed / finding |
|-------|-----|----------|-----------|-------|-------------|-----------|----------|------------------------|
| R1 | RESTYLE-ip-is85-cs125 | 0.85 | 1.25 | 20 | "watercolor control panel matching the reference style, white background" (minimal, defers to refs) | 0.16 FAIL | 0 | **Total failure.** Faint cyan wash + random confetti speckles; NO panel body, NO capsule buttons, NO knob. IP-Adapter at 0.85 did NOT transfer cobalt+capsule palette; produced noise. (gen launched by prior owner; judged here) |

| R2 | RESTYLE-ip-is85-cs15 | 0.85 | 1.5 | 30 | "...exact style of the reference images, bright, colorful controls, white background" | 0.178 FAIL | 0 | **Same failure, fainter.** Pale cyan wash + faint yellow speckle columns; still NO panel/buttons/knob. Raising cond-scale 1.25->1.5 did NOT lock the contour and did NOT help. Confirms IP-Adapter @0.85 wash overwhelms lineart regardless of cond-scale. |

## Diagnosis after R2
- Two gens at ip-scale 0.85 (cs 1.25 and 1.5) both collapse to a pale averaged cyan field. The
  reference images (whole bright panels) fed as IP-Adapter input push the model to an AVERAGE
  pale-blue wash rather than transferring discrete colorful controls. Cond-scale is not the lever.
- Answering the core question so far: **higher cond-scale did NOT pull the renders toward the
  bright colorful reference** — and IP-Adapter at high scale actively destroys structure.
- Next: drop ip-scale to ~0.6 and lean on an EXPLICIT colorful prompt (the prompt has been inert
  while IP dominated) so the lineart+prompt render the panel/buttons and IP only tints. (R3)

## Diagnosis after R1
- IP-Adapter @0.85 on dreamshaper-8 with a minimal ref-deferring prompt yields a washed-out
  speckle field, not the panel. Two problems: (a) geometry not locked (IoU 0.16 — cond 1.25 too weak
  for this control map / the wash overwhelms the lineart), (b) color not transferred.
- Next moves to test: (R2) raise cond-scale to 1.5 to force the contour; (R3) since IP-Adapter
  alone isn't pulling color, add an EXPLICIT colorful prompt while keeping style-refs, to see if
  prompt+IP together produce the bright capsule panel.
