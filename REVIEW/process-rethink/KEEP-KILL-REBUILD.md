# Keep / Kill / Rebuild — step-by-step analysis (Fable draft, pre-lane-cross-check)

Status: DRAFT — to be reconciled against L1 (retro), L5 (verified inventory), L2/L3
(external alternatives) before it becomes PROCESS-V3. Evidence cited as ledger rows.

Method: walk the pipeline stage by stage; for each element ask (a) is it PROVEN — i.e.
verification evidence exists, not just "it ran once"; (b) did it cause or enable a
recorded failure; (c) does something strictly better exist. Per user decision 1, "kept"
without fresh evidence = not kept.

## Stage 0 — Geometry source of truth

| Element | Verdict | Reason / required evidence |
|---|---|---|
| master_paths.jsx + master_paths.json (73 true bezier paths) | KEEP + verify | Vector truth straight from the .ai (S59). Required evidence: dual-source overlay — vector render vs .ai raster export, agreement within stroke tolerance; ONE human look at the overlay. |
| render_from_paths.py | KEEP | New, clean, solid strokes by construction. Same dual-source check covers it. |
| master_spec.py raster reconstruction (dilate/erode/percentile/bbox/dash-bridging) | **KILL → REBUILD** as native-vector spec builder | Caused: jagged arch (S59), synthetic wide anchor + circular validation (S58), dash leaks (S44). v3 probe proved heuristics don't transfer to clean input (body_frac 0.33 vs 0.92). Rebuild consumes master_paths.json directly: polygons from sampled beziers, exact circles for holes, zone classes from stroke color, ANY output resolution, zero morphology. |
| v2 contract JSONs / control maps / masks (current) | INTERIM ONLY | Anchor now source-verified, but produced by the raster path. Superseded the moment the vector builder lands; nothing new generated against them after that. |

Failure classes killed by construction: #1 (synthetic geometry), #6 (raster reconstruction).
New rule: any derived geometry asset ships with a machine dual-source check + overlay.

## Stage 1 — Intake / task definition

| Element | Verdict | Reason |
|---|---|---|
| Task packet (SVG key + ref images mandatory, validator enforced) | KEEP | R34/R38 enforced + tested. |
| intake-classifier skill | KEEP, amend | Add: style-spec + mood-board co-build gate becomes part of intake (user decision 2). |

## Stage 2 — Style definition

| Element | Verdict | Reason |
|---|---|---|
| STYLE-SPEC 19-field YAML + reference ROLE map | KEEP | Validated: first spec-driven round (r16) beat 15 iterated rounds on style (S54); role map fixed the r15 glossy root cause (S52/S53). |
| Mood-board as a one-shot artifact I assemble alone | **REBUILD** as co-build loop | User decision 2: skills/tools for creating mood boards WITH the user — propose axes → cheap probe tiles → structured verdict → lock → version. The board is a living, versioned gate artifact, not a poster. |
| Prose-anchored style anywhere | KILL (already law) | LAW 0; proven drift (r4 desaturation S24, description-anchored monochrome). |
| MRWC LoRA | KEEP conditionally | Re-earn: once style is co-locked, A/B the LoRA against the locked board; retrain (~$2-6, S10) if it fights the locked style. Felt-poisoned MRCH already retired (S28). |

Failure class killed: #2 (style oscillation) — by locked, versioned, co-approved board + spec.

## Stage 3 — Generation route

| Element | Verdict | Reason |
|---|---|---|
| Route D (control+LoRA init → ref-anchored restyle → mask-cut → bevel) | KEEP AS INCUMBENT, actively challenged | Best proven: IoU 0.966–0.974 with real watercolor (S31, S42). BUT restyle stage is the #1 remaining defect source: drifts internal geometry, inserts emblems (S57, S58b). If L2/L3 surface a single-pass route with style-ref lock + multi-control that matches quality, the restyle stage dies. Decide on evidence in PROCESS-V3. |
| Control maps from vector spec, solid strokes, per-panel native res | CHANGE (input source swap) | Follows Stage 0 rebuild; dash rule already binding (S44). |
| Calibrated dials (cs 0.3 default / 0.45 door; ls 1.2) | KEEP as starting points | Hard-won calibration (S57); revisit only if route changes. |

## Stage 4 — Emblems (user decision 3: painted + harder gates)

| Element | Verdict | Reason |
|---|---|---|
| Emblem handling as prompt-clause + hope | **KILL → REBUILD** as emblem card + gate + repair loop | Wrong-form 4+ rounds (S56 note). New: spec carries a drawn EMBLEM CARD (correct form, count, allowed positions). Post-init AND post-restyle: detect instances → hi-DPI crop form-check vs card (detail from crops, COUNT from whole panel — judge-needs-hidpi-crops) → auto-repair via masked Flux Fill anchored on the card, max 2 attempts → else flagged in the round form. |

Failure class killed: #3 — not by making diffusion perfect, but by making wrong emblems
unable to pass unnoticed and giving the repair a fixed, proven tool.

## Stage 5 — QA gates

| Element | Verdict | Reason |
|---|---|---|
| forbidden_gate.py (--exclude-edges) | KEEP | Calibrated good 0.86 / synthetic-bad 3.2 (S42, S51). |
| geom_gate.py mask mode | KEEP with documented caveat | Deterministically catches near-empty (right_s1, S23); false-fails legitimately-white styles (S51) — advisory on white-heavy styles. |
| hole_bevel.py / punch pipeline | KEEP | Verified on rounds; space-recipe port (S42). |
| door_anchor_gate.py as pass/fail | KILL as gate, keep overlay generator | Calibration inverted (S57). Overlay stays the arbiter. |
| Gates run ad hoc, skippable under momentum | **KILL → REBUILD** as one gate-runner | I skipped the mandatory overlay on r16/r16b (S57) — discipline failed, so discipline is the wrong mechanism. One command runs ALL panel-applicable gates → machine+visual report; entry into REVIEW/ REQUIRES the sibling report (artifact_guard can enforce at the tool boundary). |
| Gate calibration practice | NEW RULE | Every gate lands with ≥1 known-good + ≥1 known-bad case recorded (failure class #5; code-gates-need-calibration). Uncalibrated gate = advisory, never blocking. |

Failure classes killed: #4 (skipped gates — structurally impossible), #5 (miscalibration — calibration required to block).

## Stage 6 — Finish chain

| Element | Verdict | Reason |
|---|---|---|
| reupscale→dehalo→white_key, esrgan alt, native-res recut, hole re-punch, low-creativity on emblem panels | KEEP | All calibrated with documented constraints (S48, S50, S34 incidents fixed). No recorded open defect. |

## Stage 7 — Review loop (user decision 4)

| Element | Verdict | Reason |
|---|---|---|
| Free-prose FEEDBACK.md + open questions | **REBUILD** as structured verdict form | Ambiguous verdicts fed the circles. Every round ships a generated form: forced A/B picks per open decision, per-spec-field sliders, defect checklist, one free-text box. A small tool applies verdicts as spec patches (formalizes the existing verdicts-patch-spec protocol). |
| REVIEW/ single inbox, absolute path, all candidates full-size, filename link text | KEEP | Standing user rules; worked. |

## Stage 8 — Round discipline (the anti-circles core)

NEW, replaces nothing (this layer didn't exist):
- Every round DECLARES before spend: target defects (from last verdict form), the
  hypothesis (what changed and why it kills those defects), gate plan.
- **Circuit breaker:** a defect surviving 2 rounds of the same method class forces a
  method-class change (different tool family / decomposition), not a parameter tweak.
  (Badge form burned 4 rounds of same-class attempts before the class changed.)
- Feedback dual-track stays law: fix output AND process, then compare.
- Misdiagnosis guard (failure #7): any "X can't do Y" claim gets recorded with the
  falsifying test that proved it, or is marked SUSPECTED, never stated as fact.

## Open items pending lanes
- L2/L3: does a better generation route exist (single-pass style-locked)? → Stage 3 decision.
- L4: verdict-form patterns + mood-board co-build prior art → Stage 2/7 design details.
- L5: verify every KEEP above actually runs today (status column becomes evidence).
- L1: failure classes I missed → new rows here.
