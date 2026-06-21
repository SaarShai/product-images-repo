# Princess improvement — learnings (T2), judged evidence

Method tested: OpenAI crop-donor anatomy edit (crop the figure → prompt-anatomy "fix face/hands/fingers/
feet, keep pose/dress/style, same framing, no zoom" → donor). 5 fairies: door BL/BR, narrow-01 TL/ML/R.
Judged by 2 independent VLM judges per donor (original vs donor).

## What's EASY vs HARD (the core question)
- **FACE — EASY.** Every donor fixed the face (even eyes, defined nose/mouth) — judges agree (style_preserved 4–5).
- **FEET / TOES — MEDIUM, improved.** Truncated/soft feet became defined, especially on high-res source.
- **LIMB PROPORTION — MEDIUM, improved.**
- **HANDS / FINGERS — HARD.** Persistently soft / merged, not crisply five-fingered, even after the edit.
  Fingers are the single hardest anatomy element; a full-crop re-gen does not reliably fix them.
- **SOURCE RESOLUTION matters a lot.** High-res source (narrow-01, 3416×7368 → big crops) gave the
  cleanest, most composite-ready donors (n1TL: both judges ACCEPT). Low-res source (door-panel, 1088px)
  donors drifted more and one was REJECTed.

## The blocker for clean improvement (judged, both judges, repeatedly)
OpenAI's crop edit is a **full re-generation, not a localized fix**: it **re-zooms / reframes at a larger
scale**, sometimes drifts pose or even the held object (BR: indistinct item → white bird). So a donor
**cannot be masked straight back over the original** — it needs **rescale + re-registration**, and content
drift risks rejection. This is the same reframe behavior seen on the princess-window edits.

## Best path per change-type (conclusion)
- **Localized detail (face/hands at exact spot+scale) → needs MASKED INPAINT** (region-locked): Photoshop
  Generative Fill (installed) or the OpenAI Images API /edits with a mask. The judges independently
  recommended "true localized inpaint at original scale." Full-crop re-gen is good for a DONOR, not a drop-in.
- **If using a re-gen donor → register+rescale the figure to the original, then mask-composite** (prior-art
  method). Adds an alignment step; acceptable for high-res, composite-ready donors (n1TL, dpBR).
- **Hands specifically:** expect a second targeted pass (hands are hard); consider a hand-only masked inpaint.

## Status of donors (for later composite / human pick)
- ACCEPT (composite-ready, needs rescale): n1TL (both ACCEPT), dpBR (1 ACCEPT/1 PATCH).
- PATCH/REJECT (reframed too much / low-res): dpBL, n1ML/n1R pending judge (ML/R donors made, judged next).
- All donor PNGs in tasks/princess-improve/sub/PA-*.

## RESULT — register+composite validated (whole-crop-replace + feather)
Composited all 3 improved fairies (TL/ML/R donors) back into narrow-01 → `sub/narrow01-improved-all.png`.
Method: resize donor to the original crop bbox, paste into a narrow-01 copy, FEATHER the interior seam edges
(all 4 sides for an interior region; skip the side that is the panel edge). RESULT: seams blend ACCEPTABLY
for both corner (TL) and interior (ML) regions — because the anatomy prompt kept composition+style close, the
redrawn crop matches its surroundings. NOT pixel-exact (the whole crop is a redraw), but production-viable + fast.
EFFORT: low (a feathered paste). When the donor reframes more (low-res door panel) or surroundings differ, the
seam shows → then use fairy-ONLY masking or masked-inpaint. So: corner/edge fairies = easy composite; tightly-
surrounded interior detail or a pixel-exact requirement = masked-inpaint (PS Generative Fill / OpenAI /edits).

## Next experiments (different methods, to extend the learning)
1. DONE: register+composite n1TL/ML/R → narrow01-improved-all.png (seams acceptable).
2. Photoshop Generative Fill on a hand region (masked inpaint) → compare to crop-donor for hands.
3. Geometry-tighten: register each panel to the skyline/princess SVG, measure fit, see what improves.
