# Skyline results — user feedback round 1 (2026-06-21)

Verbatim verdicts + disposition. Status: A=accept, X=reject/regen, S=style-only, G=geometry.

| # | file | user verdict | class | disposition |
|---|------|--------------|-------|-------------|
| 1 | RC-door-geoA1.png | very good | A | KEEP (reading-corner door pick) |
| 2 | RC-door-geoB1.png | wrong geometry, bad style | X geom+style | regen vs corrected guide; trapezoid now gated |
| 3 | RC-door-geoC1.png | not great style | S | regen for style; geometry ok |
| 4 | RC-left-geoW2.png | very good | A | KEEP (reading-corner left pick) |
| 5 | RC-right-geoK2.png | center forbidden lane CROPS horse head | X keep-clear | regen: horse out of center lane, no crop; lane crop now shown to judge |
| 6 | GB-door-geo1.png | bad geometry + door too low | X geom+gateway | regen vs corrected guide; gateway→arch |
| 7 | GB-door-geo2.png | door too small | X gateway | regen: gateway sized+aligned to arch |
| 8 | GB-narrow-v2a/v2b.png | too narrow, too much side margin | X coverage | regen: wider tower, less margin (advisory, judge+human) |

## What changed in the workflow from this feedback
- `skyline_panel.py --mode check` is PANEL-TYPED: door = hard taper/underfill gate; narrow = ADVISORY
  (content_coverage + center-lane painted-fraction + `<out>.lane.png` crop). The old taper gate
  false-failed the GOOD narrow (geoW2) — narrows are sky-aware.
- Narrow "too narrow/margin" is NOT a clean pixel gate (good 0.79 vs bad 0.71–0.76 overlap) → advisory → judge+human.
- Keep-clear lane crop emitted (panel-relative) so the judge can catch a recognizable feature / cropped
  head in the lane (#5). judge_panel.py keep-clear crops guarded to full-template candidates only.
- judge packet now carries `geometry_spec` + `references` + `keep_clear_crops`.

## Picks so far (user-confirmed "very good")
- Reading corner: door = RC-door-geoA1.png; left tower = RC-left-geoW2.png. (right tower + door style spare: regen)
- Gingerbread: none accepted yet — all doors + narrows need regen.

## Still human-axis
- Style refinement (#2,#3): feed stronger reference IMAGES + more candidates; human picks.

---

# REGEN ROUND R (2026-06-20) — 13 candidates for the 7 rejects

Provider: `subgen.py --provider openai` (concurrent), guides = corrected domed-rectangle geoguides,
style driven by reference IMAGES (LAW 0). The 2 accepted picks (RC-door-geoA1, RC-left-geoW2) untouched.

Verdict legend: door gate = `skyline_panel --mode check` side-fill (PASS=fills contour / FAIL=taper-underfill).
narrow = content_coverage (rejected baseline was 0.71–0.76) + center-lane clean (no face/head/sign/feature, nothing cropped on lane).
Style/arch-alignment = my spec-anchored visual judgement (advisory → human decides). ADV = advance.

## RC door (style was weak — needed strong storybook, edge-to-edge fill)
| candidate | door gate | style / fill | advance? |
|---|---|---|---|
| [RC-door-geoR1.png](skyline-reading-corner/sub/RC-door-geoR1.png) | **PASS** (bl 0.00 br 0.05 ml 0.00 mr 0.07) | excellent warm-gold storybook; glowing arched gateway fills the marked arch (top reaches arch marker), owl+dragon+lanterns+moon, corners filled with books/lanterns; domed rect, no taper | **ADV (lead)** |
| [RC-door-geoR3.png](skyline-reading-corner/sub/RC-door-geoR3.png) | **PASS** (all sides 0.00) | excellent; arched story-portal, child on floating book + airship-of-books, houses+mice+boats fill both bottom corners; cleanest fill | **ADV (lead)** |
| [RC-door-geoR2.png](skyline-reading-corner/sub/RC-door-geoR2.png) | **FAIL** taper/underfill (bl 0.34 br 0.38 ml 0.54 mr 0.61) — background in bottom corners + mid sides | good style but geometry fails | drop |

## RC right tower (reject: horse HEAD cropped in center keep-clear lane)
All 3 keep the figure/horse in a SIDE column, head OFF the center lane, nothing cropped on the lane (lane crops verified). content_coverage 1.00 all.
| candidate | lane-clean (head off-lane, no crop) | notes | advance? |
|---|---|---|---|
| [RC-right-geoR1.png](skyline-reading-corner/sub/RC-right-geoR1.png) | **YES** | tower wall down center; knight on white horse LEFT base, head faces left; fairy right; star banner; only rump sliver enters lane at base, no head | **ADV (lead)** |
| [RC-right-geoR3.png](skyline-reading-corner/sub/RC-right-geoR3.png) | **YES** | tower wall down center; knight+white horse LEFT base, head left; owl on books right; clean lane | **ADV** |
| [RC-right-geoR2.png](skyline-reading-corner/sub/RC-right-geoR2.png) | YES (head off-lane) | gorgeous tree+lanterns; white horse RIGHT base grazing (head down/right, off-lane); horse body sits a bit closer to center at the very base than R1/R3 | ADV (style-strong, lane slightly tighter) |

## GB door (reject geo1: trapezoid + door too low; geo2: door too small)
Gateway must be sized+centered to saloon_arch_frac (x0.359–0.641, y0.379–0.40). All 3 PASS the taper gate (domed rect, candy-cane corner posts fill bottom corners, snowy icing dome). NOTE: arch marker y≈0.38 is high vs a natural facade; door tops sit lower than the marker on all three (less severe than the rejected geo1), but doors are large+centered (fixes geo2 "too small").
| candidate | door gate | door size/center vs arch | advance? |
|---|---|---|---|
| [GB-door-geoR1.png](skyline-gingerbread/sub/GB-door-geoR1.png) | **PASS** (bl 0.14 br 0.18 ml 0.10 mr 0.13) | large green arched door, white icing-scallop arch, centered on arch x; door top below arch-y marker | **ADV (lead)** |
| [GB-door-geoR3.png](skyline-gingerbread/sub/GB-door-geoR3.png) | **PASS** (bl 0.07 br 0.08 ml 0.10 mr 0.08) | most generous green arched door + wreath, frosted trees in corners; centered; door top below arch-y marker | **ADV (lead)** |
| [GB-door-geoR2.png](skyline-gingerbread/sub/GB-door-geoR2.png) | **PASS** (bl 0.22 br 0.23 ml 0.31 mr 0.34) | door SMALLEST + lowest, plain brown (no green), windows dominate — closest to the geo2 "too small" reject | drop |

## GB narrows (reject v2a/v2b: too narrow, too much side margin)
Fix = candy tower fills full WIDTH; quiet center holds only a straight candy-cane stripe (lane crops verified clean — no feature/window/heart centered on the lane, nothing cropped). content_coverage 0.95–1.00 (vs rejected 0.71–0.76). NOTE: all four are perfectly bilaterally symmetric, so the candy-cane stripe reads as a faint central seam splitting two mirrored halves — geometrically compliant, flag for human taste.
| candidate | panel | coverage | lane-clean | advance? |
|---|---|---|---|---|
| [GB-narrow-LR2.png](skyline-gingerbread/sub/GB-narrow-LR2.png) | left | **1.00** | YES | **ADV (lead left)** — widest, tiered-house look least seam-y |
| [GB-narrow-LR1.png](skyline-gingerbread/sub/GB-narrow-LR1.png) | left | **0.97** | YES | ADV (alt left) |
| [GB-narrow-RR1.png](skyline-gingerbread/sub/GB-narrow-RR1.png) | right | **0.95** | YES | **ADV (lead right)** |
| [GB-narrow-RR2.png](skyline-gingerbread/sub/GB-narrow-RR2.png) | right | **0.97** | YES | ADV (alt right) |

## Recommended advances (human picks final)
- RC door: **RC-door-geoR1** or **RC-door-geoR3** (both strong; R3 cleanest fill).
- RC right: **RC-right-geoR1** (cleanest lane) or **RC-right-geoR3**; R2 if style preferred.
- GB door: **GB-door-geoR1** / **GB-door-geoR3**. Open issue: door sits lower than the high arch-y marker — if user wants the door pushed up to the marker, regen with an explicit "door TOP reaches the marked arch line" instruction (or lower saloon_arch_frac.y in the spec, since a door at y0.38 is unnaturally tall for a gingerbread facade).
- GB narrows: left **GB-narrow-LR2**, right **GB-narrow-RR1**. Open issue: bilateral symmetry → central candy-cane seam; if undesired, regen asking for an asymmetric tower with an off-axis silhouette while keeping the center lane quiet.

Prompts (tracked): RC `prompt-door-geo-R{1,2,3}.md`, `prompt-right-geo-R{1,2,3}.md`; GB `prompt-door-geo-R{1,2,3}.md`, `prompt-narrow-geo-L-R1.md`, `prompt-narrow-geo-R-R1.md`.
Overlays: `<task>/sub/checks/*.ov.png` (+ `.ov.lane.png` for narrows). Judge packets: `<task>/sub/packets/<cand>/`.
