# Geometry-adherence research synthesis

## Headline

No subscription image model (gpt-image-2 via codex, Nano Banana via agy) honors exact coordinates from a prompt — geometry must arrive as PIXELS (a near-final filled base or a contract-line-art/forbidden-color map), and even then no single call locks placement; the only path to BOTH model-rendered illustrated rims AND exact coords is generate-rims-on-a-near-final-base → measure with svg_geometry_check.py → best-of-N select, with deterministic SVG re-punch reserved as the exactness backstop when the user can tolerate a code-owned cut.

## Ranked methods


### #1 Near-final FILLED base (openings as solid neutral discs at exact px) + restyle-only edit, treat layout as a CONTRACT [openai (codex exec -i base.png); secondary nanobanana (agy, base in --add-dir)]
- ref: filled base raster: exact contour + top notch + 3 hex + slot pre-drawn at correct pixels, openings as SOLID mid-grey shapes (NOT transparent/line-art)
- prompt: CHANGE: watercolor surface + paint a recessed bevelled rim ON each existing opening (soft inner shadow upper-left, lit lip lower-right). PRESERVE (enumerate each): contour, notch, hex#1/#2/#3 center+size, slot x/len/width. CONSTRAINTS: do not move/resize/add/remove/fill/round any opening; no text/hardware. Restate full PRESERVE list verbatim every iteration.
- adherence: highest of the pure-model routes. Lowest-entropy op (model only restyles pixels already in place), collapses most of the ~37% relayout drift. mean_iou should be the best in the matrix; some residual per-call drift remains (every call is a fresh sample). | rims: yes
- why: Filled beats line-art because the model sees an object to bevel, not an empty hole to paint through; gpt-image-2 can't emit transparent bg so a filled base round-trips. OpenAI's own 'change only X + keep everything else + repeat preserve list' guidance + 'contract not suggestion' framing target exactly this. This is the single biggest in-model lever and the only one that natively yields model-rendered rims at near-exact coords.

### #2 Best-of-N generate -> svg_geometry_check.py verify -> select/regenerate (test-time scaling) [openai AND nanobanana (cross-model N), via existing geom_adherence_test.py loop]
- ref: whatever base the row under test uses; verifier is the canonical SVG (svg_geometry_check.py)
- prompt: wrap any single-call method; N=4-8 independent calls, rank by mean_iou (highest) + maxpaint (lowest, hole bleed) + outside_frac (<0.02), keep best, regenerate failures with a STRONGER restated preserve list. Stop early once a candidate clears tolerance.
- adherence: converts a per-call ~60-90% hit-rate into near-certainty over a few tries. This is the reliability layer, not a standalone generator — it multiplies whatever the base method achieves. | rims: yes
- why: No subscription call is a hard lock; every gen is a random sample (OpenAI mask is soft; StructBench: leading models 'far from satisfactory'). A cheap deterministic verifier (already in repo) reliably picks the least-drifted sample. Matches loop-engineering / svg-template-review-judge. Preserves whatever rims the underlying method produced.

### #3 Contract LINE-ART / contour template as structural input, openings drawn as double-line rims, declared a CONTRACT [openai (codex -i); nanobanana (agy path)]
- ref: clean black contour + notch + hex/slot OUTLINES on white, low-contrast (mid-grey lines), rim drawn as a slight double-line so a lip is implied
- prompt: 'Use attached drawing as the EXACT structural template — preserve exact layout/proportions/positions; paint watercolor INSIDE the lines; render each opening as a rimmed recessed window, do not paint across it; do not add elements/text.' Positive object vocabulary for openings (portholes/recesses), never negation.
- adherence: good when no styled base exists yet; weaker than a filled base because a hollow outline still invites in-fill and the model relayouts more. Pair with best-of-N. | rims: yes
- why: Sketch-to-render is the documented strongest geometry anchor; double-line implies the bevel so the rim is model-rendered, not code-punched. Use low-contrast lines (SCHEMA: low-contrast refs = higher fidelity). The bootstrap step that PRODUCES the filled base for rank 1.

### #4 Deterministic SVG re-punch / clip OUTSIDE the model (artwork-only gen + exact vector cut + illustrated bevel ring drawn from SVG) [model-agnostic (openai or nanobanana for the art); cut is local Python (export_svg_template_fit.py / svg_geometry.py)]
- ref: the canonical SVG (used as clip mask + to draw the rim ring), NOT as prompt text
- prompt: artwork-only watercolor prompt (surface texture + edge language), NO template geometry in the prompt; then locally clip to true contour/notch/hex/slot and paint an illustrated bevel ring (inner shadow + lit rim) from the SVG opening geometry.
- adherence: the ONLY mathematically-exact route on the subscription tier (0% positional drift by construction). Repo memory prescribes exactly this. | rims: maybe
- why: Geometry never passes through the stochastic step, so it cannot drift. FLAG: the cut is code-owned, not model-rendered — but the bevel RING can still be an illustrated overlay, so it need not look code-punched. Use as the exactness backstop / fallback when pure-model rows miss tolerance, and as the partner of every row (accept FILL only, re-punch the holes).

### #5 Multi-image role split: geometry base = Image 1 (preserve), style ref = Image 2 (palette/brushwork only) [openai (first-image preservation bias strongest); nanobanana (label roles, keep <=5 refs)]
- ref: Image 1 = filled/contract base (geometry authority); Image 2-3 = watercolor style crops showing the rim/bevel edge
- prompt: 'Image 1 = geometry base, preserve its contour/notch/3 hex/slot exactly. Image 2 = watercolor STYLE only, borrow palette+brushwork, IGNORE its layout. Apply Image 2 style onto Image 1 geometry.' Keep total refs 3-5 to avoid role confusion.
- adherence: medium. Stops the style ref's composition leaking into geometry; ordering is a strong hint on the built-in tool (first-image richest fidelity is an edits-endpoint property, not guaranteed via codex). Layer on top of rank 1/3. | rims: yes
- why: Separates structure-source from style-source so the openings aren't redrawn to fit the style; carries the rim look from real crops rather than prose. Past ~5 refs the model rewrites Image 1 without permission (a direct drift cause).

### #6 Nano Banana Pro routing (plan-then-lock geometry) instead of Nano Banana 2 [nanobanana via agy (cannot pin Pro vs 2 per call) OR AI Studio session to force gemini-3-pro-image (no API key, Google sub)]
- ref: same filled/contract base; verify which variant ran by output tells (Pro = crisp small text + higher res)
- prompt: constraint-style prompt with Mandatory + Prohibitions blocks (Prohibitions are the stronger lever per SCHEMA ~94-95%); aspect ratio + 2K/4K request; restate preserve list each turn. Let Pro 'reason about the 4 fixed openings before painting.'
- adherence: Pro materially better at honoring a supplied layout than 2 (planner + diffusion head locked to layout); but agy can't guarantee Pro, so treat worst-case (NB2 drift) and lean on base + verify. Pro still 'tends toward realistic correction' and may auto-fix empty openings. | rims: yes
- why: The biggest Nano-side factor is plan-then-lock (Pro) vs free-redraw (2). Cross-model diversity also strengthens best-of-N. Renders rims when openings are framed as illustrated objects.

### #7 Coordinate + grid + aspect-ratio spatial language as a SECOND layer on top of the base [openai and nanobanana (prompt text only)]
- ref: none new — words that corroborate the attached base (aspect ratio first, then thirds/percentage positions for notch + 3 openings + slot)
- prompt: 'Tall narrow ~1:3 portrait. Notch centered top edge. Hexes stacked upper-middle third, evenly spaced. Slot lower two-thirds, centered, ~10% width.' Numbers REINFORCE the base; never the sole control.
- adherence: low alone (models don't honor pixel coords; NB hits 'token scarcity' on dense rules), measurable as a corroborating layer. Use only with rank 1/3, never standalone. | rims: maybe
- why: Reported layout-consistency gains exist for explicit spatial language but only as reinforcement; as the primary control this is the ~37%-drift failure mode. Keep openings as objects so rims still render.

### #8 Forbidden-color / chroma region map (magenta openings) — value is the QA channel, NOT the instruction [openai and nanobanana]
- ref: base with openings filled a single unmistakable forbidden color (e.g. #FF00FF)
- prompt: POSITIVE framing only: 'the magenta regions are recessed ports — paint a bevelled rim around each, the recessed center stays empty.' NEVER 'avoid/do not paint the magenta' (negation makes the model add it). Post-process: detect any non-magenta paint inside those masks to down-rank/clear.
- adherence: low as an instruction (models routinely paint over forbidden colors), but gives a near-zero-cost detectable 'did paint invade a cutout' signal that feeds the best-of-N verifier and the re-punch step. | rims: maybe
- why: Documented to backfire if phrased as negation; a flat filled region also invites a flat fill that kills the rim. Keep it as a cheap QA channel, not a geometry guarantee. Rim only if framed as an object.

### #9 input_fidelity=high / API masked-edit endpoint (CEILING MARKER — out of scope, subscription-unreachable) [neither (OPENAI_API_KEY + org verification + render-studio; not codex/agy)]
- ref: alpha mask + base (gpt-image-1.5/1 edits endpoint)
- prompt: client.images.edit(model, image=base, mask=alpha, input_fidelity='high'). Documented only to mark the ceiling.
- adherence: would NOT fix positional drift even if reachable: input_fidelity preserves texture/likeness not geometry and is unsupported on gpt-image-2; the API mask is explicitly SOFT ('may not follow its exact shape with complete precision'). The local SVG re-punch beats it for literal exactness. | rims: no
- why: Listed so the team doesn't chase it. Subscription pipeline cannot reach it (needs an API key = render-studio, OUT OF SCOPE per skyline decision). No model-rendered-rim advantage over rank 1.


## Test matrix


- [P1] **E1-filled-base-openai** (openai): ref=near-final FILLED base (openings = solid mid-grey discs at exact px); prompt=restyle-not-redraw; CHANGE/PRESERVE/CONSTRAINTS; bevel as surface treatment ON existing edge; enumerate each opening; hyp=Filled base + restyle-only gives the highest mean_iou and lowest maxpaint of any single-call route, and renders illustrated rims natively. This is the baseline-to-beat.

- [P1] **E2-filled-base-nano** (nanobanana): ref=same FILLED base as E1; prompt=constrained EDIT ('use as exact base, repaint interior only, keep everything else the same'); Mandatory + Prohibitions blocks; hyp=Same base on Nano Banana: tests whether agy's variant (2 or Pro) can match OpenAI on a low-entropy restyle. Cross-model diversity for best-of-N. Expect more drift if NB2 is routed.

- [P1] **E5-bestofN-openai-filled** (openai): ref=FILLED base (E1 config); prompt=best-of-N (N=6): same prompt, select highest mean_iou + lowest maxpaint via geom_adherence_test.py, regenerate failures; hyp=Best-of-N over E1 lifts the accept-rate from per-call ~60-90% toward near-certainty within the budget. Measures how many tries to clear tolerance — the core reliability number.

- [P2] **E3-lineart-contract-openai** (openai): ref=contract LINE-ART contour (low-contrast, openings as double-line outlines); prompt='exact structural template, layout is a CONTRACT'; openings as rimmed portholes (positive vocab); no negation; hyp=Line-art drifts MORE than the filled base (hollow outline invites in-fill) but still renders rims; quantifies the filled-vs-lineart gap that justifies pre-baking a filled base.

- [P2] **E7-multiref-roles-openai** (openai): ref=Image1 = filled base (geometry), Image2-3 = watercolor style crops; prompt=numbered-refs: 'Image1 geometry preserve exactly, Image2 style only, ignore its layout'; hyp=Role-split keeps style-ref composition from leaking into geometry (mean_iou >= E1) while improving rim/edge realism. Tests first-image-preservation bias on the built-in tool.

- [P2] **E9-nano-pro-route** (nanobanana): ref=FILLED base; inspect output to detect Pro vs 2; prompt=constraint prompt + 'reason about the 4 fixed openings before painting' + 2K/4K + aspect ratio to bias toward Pro behavior; hyp=When agy routes to Nano Banana Pro (plan-then-lock), mean_iou beats E2/E4; records whether agy can be nudged toward Pro and the adherence delta when it lands.

- [P2] **E10-artwork-only-repunch-openai** (openai): ref=NO geometry in prompt; canonical SVG used only for local clip + bevel ring; prompt=physicalize via post-process: artwork-only watercolor gen, then deterministic SVG re-punch + illustrated bevel ring overlay; hyp=Establishes the exactness ceiling: 0 positional drift by construction. FLAG: cut is code-owned (model does not render the holes), so it's the fallback/backstop, not the model-rendered-rim target. Benchmarks how far pure-model rows are from exact.

- [P2] **E11-restyle-vs-redraw-openai** (openai): ref=FILLED base (E1); prompt=ablation: same base, prompt = full free REDRAW ('repaint this panel as watercolor') with NO preserve list; hyp=Reproduces/quantifies the ~37% drift baseline on OUR panel, isolating the value of the restyle-not-redraw + preserve-list lever (E1 minus the preserve discipline).

- [P3] **E4-lineart-contract-nano** (nanobanana): ref=same LINE-ART contour as E3; prompt='follow the structure of the attached reference exactly'; Prohibitions block; keep-everything-else clause; hyp=Nano on line-art: isolates model effect at the line-art reference level vs E3. Likely the weakest geometry of the matrix if NB2 is routed.

- [P3] **E6-coords-layer-openai** (openai): ref=FILLED base + coordinate/grid/aspect prose layer; prompt=explicit-coords as REINFORCEMENT on top of E1 base (thirds/percentages for notch+3 openings+slot); hyp=Adding coordinate prose on top of the base marginally improves mean_iou over E1; isolates the corroboration value of numbers (expected small, positive).

- [P3] **E8-magenta-qa-openai** (openai): ref=FILLED base with openings in forbidden color #FF00FF; prompt=POSITIVE chroma framing ('magenta = recessed port, paint rim around, center stays empty'); no negation; hyp=Magenta gives a near-zero-cost detectable 'paint invaded a cutout' QA signal (maxpaint inside magenta), even if it doesn't improve placement vs E1. Validates the cheap verifier channel.

- [P3] **E12-bestofN-crossmodel** (nanobanana): ref=FILLED base; pool OpenAI (E5) + Nano candidates; prompt=cross-model best-of-N: pool both vendors' candidates, select by the same geometry metrics; hyp=Mixing OpenAI + Nano candidates yields a higher best-of-pool accept-rate than either alone, because failure modes are partly independent. Tests vendor diversity as a reliability lever.

- [P3] **E13-iteration-drift-openai** (openai): ref=FILLED base; chain output->input across 3 turns vs always re-attach base; prompt=single-shot-from-original discipline: compare chaining the last output as the new ref vs always restarting from the canonical base; hyp=Chaining output->input accelerates drift (PIED), measurable as mean_iou decline turn-over-turn; re-attaching the canonical base stays flat. Validates the never-chain rule.