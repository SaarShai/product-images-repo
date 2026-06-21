# REVIEW — retrospective of the work so far (self-audit)

Source: this session + .claude memory + .brainer ledger + wiki. Dense notes.

## Task classes we actually ran
1. Redraw/restyle ONE element, change nothing else (fairies; taxi cabs).
2. Reshape an embedded element to exact dims (widen window + flat bottom).
3. Remove an element + reconstruct bg (mid taxi; TAXI text/signs).
4. Move/relocate an element (taxi swap).
5. Fit artwork to die-cut SVG contour + holes (skyline/door panels — prior).
6. Judge candidates (geometry + style + defects) and gate.

## SUCCESSES (keep / standardize)
- **Diff-mask composite + measured gate** (`compose_fairy.py --diffmask`): outside-mask delta gate = 0. Reliable "change nothing else" — when the engine localizes its change.
- **Flux Fill (masked inpaint) for SAME-footprint redraw**: localized change → clean composite, no seam. Beat free-redraw engines in busy scenes.
- **Bria eraser (fal-ai/bria/eraser) for REMOVAL**: deletes masked content + reconstructs bg IN watercolor style. Far better than flux-fill for removal.
- **Engine routing**: Flux.2-pro = complete figures; Kontext = style cohesion; Flux Fill = masked redraw; Bria = removal; local SDXL+LoRA+IP = free fallback.
- **Geometry guide locks aspect** for die-cut panels (grey guide as image-1 to gpt-image).
- **Multi-judge on hi-DPI crops**; count on whole-panel context (tiles hide duplicates).
- **Stretch-then-refine** for exact reshape (PIL stretch → Kontext cleanup → arched-mask composite).
- **Reference-lock** (Flux.2 image_urls[] / IP-Adapter) for cross-instance consistency.
- **Subscription/secret hygiene**: keys in .secrets gitignored; wrappers not ad-hoc CLI.

## FAILURES / USER FEEDBACK (fix these)
- F1. **Kontext REFRAMES/zooms** (recentred the cab, erased buildings) → unusable in place for "keep position".
- F2. **Diff-mask SEAMS in busy scenes**: global-repaint engine → diff>thresh everywhere → mask = bbox rectangle → visible seam ("the composing doesn't look right"). Fixed by switching to masked-inpaint, but the FAILURE MODE recurs whenever we pick the wrong engine.
- F3. **flux-fill HEALS text back / ADDS cars** ("no text"/"no car" negatives weak). Wasted 2 gens before switching to Bria.
- F4. **MASK EYEBALLING ~100px off, repeatedly** (door text, roof sign): >6 wasted iterations + several wasted API calls this turn alone. THE bottleneck.
- F5. **Eyeballed target overlay was wrong** (window magenta estimate "not good") → needed user labeled-grid handoff.
- F6. **Style drift toward realism / glossy** (fairy BR doll, K3 anime) when guidance high or refs weak.
- F7. **VLM judge downsampling hallucination** on tall panels; aesthetics not rankable; over/under-count.
- F8. **OpenAI gpt-image restyles globally** even with a mask (bolder ink) → style mismatch.
- F9. **Geom region-IoU lies about holes** (enclosed-void clarity needs a different check).

## BOTTLENECKS (rank — "the bottleneck gets the hammer")
- B1 **Mask generation** (manual, eyeballed) — slowest, most error-prone, blocks every masked op. HAMMER FIRST.
- B2 **Verification is manual** — I eyeball every crop; no automated style/defect/leftover-text/geometry checks in-loop.
- B3 **Engine selection is ad-hoc per task** — re-derived each time; no routing rule encoded → wrong-engine failures (F1/F2/F3).
- B4 **Geometry fitting** to exact SVG still weak (guide-only).
- B5 **Serial fal calls** — one image at a time; slow fan-out.
- B6 **No regression/eval set** — can't objectively prove an improvement or catch regressions.

## What "perfect" looks like for the loop
crop → (auto-mask from text/click) → route to correct engine by task-type → gen (parallel candidates) → diff-mask composite + pixel gate → AUTO VLM/defect/OCR/geometry checks → accept/patch/restart, all logged + cached + reproducible, validated on a fixed eval set.
