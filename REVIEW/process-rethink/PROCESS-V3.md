# PROCESS-V3 — the redesigned pipeline (proposal, awaiting user approval)

Synthesized from: RETRO.md (22 failure modes F01–F22 + prevention rules), FAL-CAPABILITIES.md,
OSS-LANDSCAPE.md, PROCESS-PRIOR-ART.md, KEEP-KILL-REBUILD-DRAFT.md, and the user's 4 binding
decisions (RETHINK-GOAL.md). Status: PROPOSAL. No regeneration spend until approved.

Asset base verified (ASSET-INVENTORY.md, L5): 161 items WORKS-VERIFIED incl. full test
suite 49 passed/3 xfailed; all 3 LoRAs COMPLETED with local weights; geometry v2 assets
valid (5 spec.json + 24 PNGs); all 5 venvs import; secrets present. The KEEPs below are
verified, not assumed. Notables: 3 scripts flagged UNUSED; dup_prefilter.py needs
.venv-gen, not system python.

## Design laws (each traceable to a recorded failure)

1. **Vector truth first.** All geometry derives from the .ai bezier paths (master_paths.json);
   raster reconstruction is dead. Every derived geometry asset carries provenance + a
   dual-source equivalence check. Generator and judge NEVER share an unverified derivative.
   (F02/F03/F16/F17; RETRO Rule A1)
2. **Style is a versioned STYLE BIBLE, not a knob.** 19-field spec + role-locked refs +
   motif sheet + color script, co-built with the user, versioned; prompts compile FROM it;
   every gen records a render trace (prompt hash, refs-by-role, engine, seed). (F06–F08, F10;
   PRIOR-ART practices 1–3, 7)
3. **Phase gates with locks.** rough → cleanup → color/finish → prepress. A later phase
   cannot change an earlier phase's approved dimension; every retake names its phase
   (RESET_STYLE / ROUGH_RETAKE / CLEANUP_RETAKE / COLOR_RETAKE / PREPRESS_RETAKE) plus
   must-preserve / may-change. (PRIOR-ART practices 4–5; F22)
4. **Gates are structural, not disciplinary.** One gate-runner command produces the full
   bundle (measured geometry + overlays + forbidden + emblem crops + dimensions); a candidate
   without a bundle cannot enter REVIEW (artifact_guard enforces). PASS ≠ approval — the
   overlay and the user stay arbiters. (F01, F04, F16 — the skipped-gate class; RETRO Rule C2)
5. **Model output is a candidate/donor, never authority.** Post-restyle and post-finish
   re-gate always (restyle inserts emblems; finish bites edges). (F14, F15, F21; Rule A4/D2)
6. **Circuit breaker.** A defect surviving 2 attempts of the same method class forces a
   method-class change — never a third parameter tweak. (F15 badge ×4; Rule D1 + Kontext
   multi-turn degradation warning)
7. **Providers are untrusted until measured.** Every call returns a measured-artifact record
   (actual W×H, model, seed); downstream consumes only that. (F20; Rule D3)
8. **Structured verdicts every round** (user decision 4). Axis verdicts + retake label +
   crop ids + must-preserve; verdicts auto-patch the bible/spec version. (PRIOR-ART §4)
9. **Claims carry evidence.** "X can't do Y" recorded with its falsifying test or marked
   SUSPECTED. Route docs versioned + falsifiable, never "solved". (F18, F14-narrows; Rule C1)

## The pipeline

```
A. TEMPLATE DECODE (vector)        → panel contracts + control bundle + dual-source proof
B. STYLE BIBLE co-build (w/ user)  → bible v1: spec + roles + motif sheet + color script
C. ROUGH gate (cheap)              → composition/silhouette/motif placement approved
D. GENERATION (route by bake-off)  → candidates behind the gate-runner
E. CLEANUP gate                    → emblem/motif crop checks + bounded repairs
F. COLOR/FINISH gate               → palette vs color script; faithful-vs-creative upscale
G. PREPRESS gate                   → holes/bevel/keep-clear/vector-overlay/export manifest
H. REVIEW (every round)            → structured verdict form → auto-patch bible → next round
```

### A. Template decode — REBUILD (the one big new tool)
`scripts/vector_spec.py`: consumes tasks/_templates/master_paths.json directly.
Polygons sampled from beziers; holes as exact circles; zones classified by stroke
color+dash; emits per-panel spec.json + control maps (solid strokes, any resolution) +
masks + forbidden + anchor. Verification: renders vs the .ai raster export, machine
agreement score + ONE human overlay look. Kills master_spec.py's raster heuristics.
(Existing master_paths.jsx re-runs read-only whenever the template changes.)

### B. Style bible co-build — NEW SKILL, WITH the user (decision 2)
Loop: (1) I derive candidate axis values from collection refs → (2) generate a PROBE
BOARD — small cheap tiles varying ONE axis each (medium, palette, line, detail density…)
→ (3) user answers a forced-choice form (A/B per axis + sliders + mood words) → (4) bible
v1 locked; motif sheet (crops of every recurring element: badge, windows, signage blanks,
vehicles + "never" anti-crops) + color script (3–8 swatches + warm/cool poles + luminance
note per panel) → (5) later corrections arrive as verdict-form entries that bump the
bible version. The board costs ~$1–3 of tiles; misunderstandings die here instead of in
full-panel rounds.

### C. Rough gate — NEW (cheap, kills late discovery)
Per panel: 2–4 low-cost composition candidates (init-stage output is fine) shown at
small size WITH cut overlays. User verdict: composition + motif placement only (form
forbids style talk at this gate). Approved rough = geometry+composition LOCK.

### D. Generation — bake-off, then commit (evidence over incumbency)
Candidates, all behind the same gate-runner:
- Incumbent: Route D (flux-control-lora-canny init cs 0.45/0.3 → flux2edit restyle).
- Challenger 1: **fal-ai/flux-general single-pass** — LoRA + ControlNet(+Union) +
  IP-Adapter + reference_image in ONE call ($0.075/MP). If style holds at geometry, the
  restyle stage (our #1 drift source) dies. (FAL §N1/N2)
- Challenger 2: Route D with **flux-kontext-lora** restyle ($0.035/MP) — the restyle
  itself carries the style LoRA + resolution_mode=match_input (less drift pressure than
  flux2edit).
Bake-off = door panel (hardest: internal cuts + anchor), 2–3 seeds each, same bible,
gate bundles + user A/B. Commit to the winner; record the route doc as versioned +
falsifiable (law 9).

### E. Cleanup gate — emblems PAINTED + harder gates (decision 3)
`scripts/emblem_gate.py`: detect instances (automask by prompt / template match) →
hi-DPI crop per instance judged against the MOTIF SHEET card (form/color/proportions)
→ COUNT on the whole panel (not tiles). Runs post-init AND post-restyle AND post-finish.
Repair: masked Flux Fill anchored on the motif card, max 2 attempts (law 6), then the
retake taxonomy's fallback (deterministic stamp composite) is OFFERED in the verdict
form — user chooses, keeping the painted-first policy intact.

### F. Color/finish gate
Palette check vs the color script (per-surface + poles). Finish chain gains a FAITHFUL
branch: fal AuraSR (4x, overlapping tiles) / fal ESRGAN / local Real-ESRGAN for
geometry-critical panels; clarity (creativity ≤0.5) only when detail rebuild is wanted;
low creativity (0.4) on emblem panels. Post-finish invariants: alpha/mask equality,
protected-pixel diff, actual-size check, no-new-marks scan. (F14; FAL §N4)

### G. Prepress gate
holes punched + bevel + keep-clear verified + signage blank + text/logos as vector
overlay in the .ai (existing law) + export manifest (layers, DPI, guide layers off).

### H. Review — structured verdict form (decision 4)
Every round ships ONE form (PRIOR-ART "Fast Review Form" adapted): axis verdicts
(style family / geometry / motifs+crop-ids / palette-finish / prepress), overall next
action (accept / local repair / phase retake / reset), must-preserve, may-change, and
an A/B section when I'm uncertain. `scripts/verdict_apply.py` turns the answers into
bible/spec patches + the next round's declared hypothesis. FEEDBACK.md stays as the
narrative wrapper; the form is the contract.

## Round discipline (anti-circles, standing)
Before spend: round declares target defects + hypothesis + gate plan. After: dual-track
(output fix AND process fix). Circuit breaker per law 6. Open user decisions are
blocking states, not backlog prose (F22).

## Build list (order of work once approved)
1. `vector_spec.py` + dual-source verification (Fable — precision core) — kills F16/F17 permanently.
2. `gates.py` runner + REVIEW-entry enforcement in artifact_guard (builder + Fable review).
3. Style-bible schema + `bible_lint.py` + render-trace in falgen/onepass wrappers (builder).
4. Mood-board co-build skill + probe-board generator (Fable designs, builder scaffolds).
5. `emblem_gate.py` + motif-sheet builder (Fable — vision-critical).
6. `verdict_apply.py` + form generator (builder).
7. falgen: flux-general / kontext-lora / aura-sr / esrgan modes + measured-artifact record (builder, from FAL report's schemas; probe cheap params first).
8. Bake-off probe (§D) — first spend, ~$2–4.
9. Skills rewritten to V3 (style-executor, geometry-executor, review protocol) (builder + Fable).
Parallelizable: 1‖3‖4‖6; 2 and 5 after 1; 7 anytime; 8 after 1–7; 9 last.

## What V3 explicitly stops doing
- Generating against any geometry without a dual-source proof.
- Prose-anchored style; role-less refs; seed-as-style-lock.
- Unlimited same-method retries; "solved" claims without fixtures + expiry.
- Free-prose-only review rounds.
- Trusting requested dimensions, IoU alone, or uncalibrated gates as blocking.

## Marriott under V3 (after builds)
A: vector contracts re-emitted + verified (fresh evidence per user decision 1).
B: hospital bible co-built from existing spec/mood-board as the starting draft — the
user's first probe-board verdict upgrades it from assumed to approved.
C→H: rough gate → bake-off → winners through cleanup/color/prepress → structured
verdicts each round. Existing r16d etc. enter as bake-off references, not finals.

## done means (for the rethink itself)
- User approves/amends this document (structured approval: per-section OK or retake).
- Build list items 1–7 land with their own verification evidence.
- Bake-off run + route committed with a versioned route doc.
- First Marriott V3 round delivered with the full gate bundle + verdict form.
