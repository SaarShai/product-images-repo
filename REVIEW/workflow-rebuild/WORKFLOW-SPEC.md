# WORKFLOW-SPEC v0 (draft for user markup) — v2 panel-illustration pipeline

Status: DRAFT — awaiting user markup. Sources: user notes (ledger S78–S89), research
lanes R1b/R2/R3/R4 (tasks/workflow-rebuild/research/), R1 pending. Collection-generic;
hospital DOOR panel = acceptance test (E5 baseline to beat).

---

## 0. The one-sentence contract

Template SVG + theme in → approved panel set out, where **every step emits a
reference IMAGE artifact that feeds the next step** — prose never carries style
or geometry (LAW 0; measured: ref+text IoU 0.9989 vs text-only 0.8352, R4 L1).

## 1. DECISIONS FIRST (the parts your markup most likely changes)

**D1. The Reference Stack — one ref image per property, one role per ref (R4 L7).**
Per collection, built once, versioned:

| slot | content | how made | user gate |
|---|---|---|---|
| medium_ref | art-medium swatch tile (e.g. transparent watercolor, mild visible bleed/texture) | harvest crop OR one cheap probe gen | pick from board |
| palette_ref | dominant-palette sheet: swatches + a painted mini-vignette in that palette | generated probe | pick from board |
| style_ref | illustration-style exemplar (toy-like, blocky, colored lineart, plush-rounded…) | harvested (hold-out rule R4 L8) | pick from board |
| feature_refs[] | per-feature card (teddy, siren, cross-badge…) — element sheets generated FIRST, then reused everywhere | generate-elements-then-compose (R2 §21) | M/N/X per feature |
| geometry_ref | grey-body guide from TRUE SVG — solid strokes only, no dashes, no in-body text, no flap outlines (R4 L5, flap lesson) | deterministic (master_spec/skyline_panel) | pixel-verified vs source |
| layout_ref | feature-placement zones drawn as simple SHAPES in place (never text labels — annotation text = leakage risk, R3 §3.6-8) | deterministic from feature-callouts YAML | diagram approval |

Ref hygiene (R1): SEPARATE files to the model, contact sheets = human/audit
artifacts only; default 3–5 refs, add a ref only after naming the missing property
on an observed failure; role names live in the PROMPT, never burned into the ref;
strip ALL text/logos/watermarks from refs; feature_refs depict the feature already
in its target state/pose (e.g. teddy already waving from a window).

**D2. Brainstorm steps (you = decider).** Two user touchpoints per collection:
(a) property boards — one row per axis above, 2–4 labeled options + "none",
forced-choice form (~5 min); (b) feature menu M/N/X + layout routes + **top-contour
routes**: agent proposes 3–4 top shapes filling the template's top bound (dome /
central tower / gable / turret…) — the dome outline is a BOUND, not a mandate;
E7's tower is the exemplar. Home: amend existing moodboard-cobuild skill, not a new one.

**D3. Generation routes (experiment matrix, not a single bet).** All gpt-image-first:
- **A. restyle-from-init** (E5 winner): init image + ref stack → free codex gpt-image.
- **B. guide-gen** (E7): geometry_ref as image[0] + ref stack → free codex.
- **C. paid exact-frame**: gpt-image-2 via fal, custom size (multiple-of-16, ≤3:1,
  832×1184 valid) — finals only.
- **D. weighted-ref side lane**: fal flux-general — the ONLY endpoint with per-ref
  strength (ip_adapter scale + reference_strength + control_lora scale, R1b) — for
  experiments needing style/geometry weight separation.
- **E. one-pass flux control-LoRA rerun** (0.975–0.988 IoU on cap-juluca, R4 §43) —
  re-verify on hospital before trusting.
Prompting: indexed-role convention — "Image 1: geometry guide… Image 2: medium…"
(OpenAI-documented, R1b); image[0] position carries extra fidelity weight.
CAVEAT (R1): gpt-image role-separation is officially documented but practitioner-
UNVERIFIED — the P5 ablation (separate-vs-sheet, shuffled order) is the deciding test.

**D4. Composition rules baked into refs + rubric (your two new guidelines).**
- complete-building: edges deliberately drawn, slight (<~2% width) detail overhang
  welcomed, hard-crop penalized — judge rubric axis + prompt clause + exemplar boards
  (REVIEW/workflow-rebuild/complete-building-exemplars.jpg + space-narrow-exemplars.jpg).
- edge-treatment recipe (extracted from space production finals): treat the die-cut
  contour as the OBJECT'S OWN EDGE — painted rim/border band tracking the contour,
  corner hardware (screws/trim) acknowledging the edge, cutouts integrated with
  painted frames. This is the concrete mechanism behind "self-contained".
- GEOMETRY-EMBRACE (user-flagged IMPORTANT, space = gold standard): the art must
  work WITH the contour/silhouette AND the cutouts — not merely avoid them. Every
  opening gets a painted frame/rim that makes it a design feature (porthole, vent,
  slot, window); the void itself stays clean (punched-holes rule unchanged). Judge
  rubric gets a dedicated axis: silhouette-embrace + per-cutout integration score.
- top-contour freedom: any intentional architectural top within the bound; no sky
  background fill.

**D5. Where you sit in the loop:** (1) property boards verdict, (2) feature/layout
M/N/X, (3) spec markup (this doc), (4) final candidate verdicts. Everything else
agents + gates.

## 2. THE PIPELINE (step DAG — each step's output = next step's input)

```
S0 template intake      SVG → geometry spec + masks (deterministic; pixel-verify derived shapes vs source — R4 L5)
S1 property brainstorm  boards per axis → USER picks            [zero/cheap spend]
S2 reference synthesis  picks → Reference Stack (D1), probe-validated tiles   [~$1-2]
S3 layout planning      feature callouts YAML → layout_ref (shapes-in-place) + diagram → USER M/N/X
S3b guide vision-gate   EVERY model-facing guide artifact gets a frontier-VISION review
                        before any gen consumes it — code gates are blind to visual
                        semantics (L2 incident: white stripe channels + topiary slab
                        passed all code checks); count>1 features = N separate shapes;
                        keep-clear zones NEVER drawn into model-facing guides
S4 generation fan-out   routes A/B(/D/E) × prompt variants, parallel, free codex first
S5 gates (auto)         two-gate MANDATORY: geom (dual metrics + overlay, R4 §47) + VLM content judge;
                        per-prop presence; emblem/motif COUNT (re-run POST-any-restyle, R4 §51);
                        forbidden stripes; complete-building axis; DOOR-FILL vs true anchor
S5b overlay law (HARD)  NO geometry verdict without a REGISTERED OVERLAY (traced
                        control lines composited on the candidate) + metric cited —
                        by leader, agents, or VLM judges alike; "by eye" on a raw is
                        banned (user rule, round-2 door incident: raws looked right,
                        overlay showed doors at ~60% of anchor). Overlay source =
                        traced control geometry, never a synthesized shape.
S6 local repair         masked region edits only (documented enforcement, R3 Recipe C); never re-seat over a good raw (R4 L6)
S7 finals               winner → route C exact-frame; upscale; Images/finals per house rule
S8 verdict              full-size boards + verdict form → USER; review boards carry an
                        OVERLAY row per candidate alongside the clean row
```

## 3. EXPERIMENT MATRIX (P5 — wide, cheap-first; purpose = learn)

Axes: route (A/B/D/E) × ref-stack ablation (full stack / style_ref-only / no
layout_ref / contact-sheet-vs-single-ref format) × image-order (geometry first vs
style first) × annotation test (shapes-only vs labeled — measure leakage, R3 gap).
All on DOOR panel, free codex path, gates auto-scored, one board per round.
Rounds run as UNATTENDED CLOSED LOOPS (generate → gates → retry-until-bar,
budget-capped, loop-engineering-linted, separate verifier — never self-graded);
user sees boards, not iterations. Gen-lane briefs carry explicit spend budget +
decision authority; frontier lanes get goal-shaped briefs (bar, not procedure).
Also probes: codex→gpt-image-2 free? (S74); OpenAI size-enum vs pixel-budget
discrepancy (R1b gap) — one cheap API call each.

## 4. BUILD BACKLOG (P4 — delegated lanes, verified before permanent)

1. ref-stack builder (`style_handle/` dir + manifest, extends build_reference_style_packet.py)
2. layout_ref renderer from feature-callouts YAML (shapes-in-place, no text)
3. emblem/motif count gate (`emblem_gate.py`) + per-prop presence check
4. measured-IoU on EVERY candidate by default + overlay always
5. falgen `.artifact.json` full-args fix (t1 provenance loss)
6. moodboard-cobuild amendments (top-contour routes, complete-building axis, property boards)
7. probe scripts (S74 free-image-2; size contract)

## 5. done means (acceptance for the whole rebuild)

1. New collection → approved DOOR panel in ≤3 user touchpoints beyond verdicts.
2. Every generation call consumed ≥3 role-tagged reference images, zero prose-only runs.
3. Every candidate carries measured geometry (dual metrics + overlay) + VLM content verdict — no IoU-only accepts (R4 L3).
4. Emblem/prop counts gate-checked post-restyle; zero duplicate-emblem escapes.
5. Hospital DOOR rerun through v2 beats or matches E5 on your verdict.

## 6. Load-bearing questions (≤3)

1. **Brainstorm depth**: property boards per COLLECTION only, or re-run per panel
   type (door vs narrow) when roles differ? (default: per collection + mini-pass per panel type)
2. **Spend ceiling per experiment round** during P5 (default: free codex unlimited + ≤$3 paid probes/round)?
3. **feature_refs**: generate a reusable element library per collection (more up-front
   cost, consistency payoff via reference-lock), or harvest-only? (default: generate library)
