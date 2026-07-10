---
scope: this-repo
kind: sop
---

# WIKI DRAFT — Generation-first transparent product images

> **Status: DRAFT, not yet in `wiki/`.** This file is the write-gate INPUT for a
> future `wiki-memory` write, not a wiki page itself. Do not treat it as
> queryable memory until it passes `write-gate` and is filed under
> `wiki/L3_sops/` (procedure) and/or `wiki/L2_facts/` (the individual measured
> facts). Companion skill (the executable form of this SOP):
> `skills/transparent-product-image-gen/SKILL.md` (status: proposed).

## Summary

For a NEW product illustration that needs a transparent background, generating
it transparent from the start (OpenAI `gpt-image-1`, `images/generations`,
`background=transparent`) beats every background-removal-after-the-fact route
tried this session — including removal from an image this same model produced
opaque. The generation-time alpha is real and, with one added prompt block
("edge-hygiene"), clean enough to use directly. For an EXISTING finished
illustration, no generation/regeneration route is source-preserving; only
correction-led matting (Adobe semantic proposal + `assisted_bg_remove.py`) with
a frozen machine gate and mandatory native-resolution human review is accepted.

## Procedure

1. **New image → generate transparent, don't remove-after.**
   `POST https://api.openai.com/v1/images/generations`,
   `model=gpt-image-1`, `background=transparent`, `quality=high`, `size`
   matched to aspect (`1024x1536` used for portrait product art), prompt ending
   in the edge-hygiene block (verbatim):
   > "every object has clearly defined, fully closed outlines; no shape fades
   > into the background; edges crisp; interior highlights enclosed by visible
   > outlines"

   Measured lever size: stray fully-enclosed background pockets in the alpha
   (a noisy-mask symptom) went from **79–169 per image → 1** with this block
   appended, same model/prompt/motif otherwise. Semi-alpha fraction also fell
   to ~0.3% of frame. Key: `.secrets/openai.env`.

2. **Upscale without corrupting alpha.**
   `tasks/double-marine-bed-wrapper-batch/alpha_aware_upscale.py --method split
   --scale 8` — RealESRGAN runs on RGB only; alpha is resized independently via
   Lanczos and recombined. Verified: alpha MAE 0 / max-error 0 vs the Lanczos
   reference, source SHA-256 unchanged. `--method direct` (undocumented native
   ncnn RGBA) and `--method two-plate` (nonlinear black/white-plate recovery,
   leaks foreground texture into alpha) are inferior — not used in production.

3. **Need a flat key color instead of alpha (same model, same call shape):**
   `background=opaque` + prompt suffix demanding a named pure color, "flat
   solid fill, no watercolor texture in background" (this last phrase was the
   effective lever vs a plain color request). Pick the key color per image —
   it must be absent from the art's own palette. Measured: 68.8% ΔE<5 to the
   model's own actual fill color, 0% edge-band spill, only 4 enclosed pockets
   — best of 3 keyable arms tried (vs Recraft V4 wrong-hue and Flux/dev
   ignoring the instruction entirely). Still requires a real despill/key
   algorithm downstream, not a one-shot perfect key.

4. **Existing image, background removal (no generation touches it):**
   Adobe MCP connector's remove-background action → semantic proposal (alpha
   seed, not a final answer) → `tasks/double-marine-bed-wrapper-batch/assisted_bg_remove.py
   --backend vitmatte` (+ sparse red/blue correction strokes only where the
   proposal is visibly wrong; `--correction-unlock-radius` narrow, ~24, not
   wide) → frozen gate
   `tasks/double-marine-bed-wrapper-batch/bg-benchmark/verify_bg_solution.py`
   → **mandatory user review** of the native-resolution white/gray/black/
   magenta composite before any candidate can move to `Images/finals/`.
   `machine_pass=true` is printed as `PENDING_HUMAN_REVIEW`, not approval.

## Evidence links

- `REVIEW/marine-bg-complete/image14-gen-api/INDEX.md` — the OpenAI API
  transparent-generation probe (P1/P2/P2b/P2c arms); source of the
  edge-hygiene lever measurement and the `images/edits` timeout finding.
- `REVIEW/marine-bg-complete/gen-model-matrix/INDEX.md` — 4-model comparison
  (Recraft V4, Flux/dev, gpt-image-1, LayerDiffuse) for both native-transparent
  and keyable-background questions.
- `REVIEW/marine-bg-complete/gen-transparent-x8/` — x8 alpha-aware upscale
  review board + native 1:1 edge crops for the accepted turtle generation.
- `REVIEW/marine-bg-complete/INDEX.md` — image15/sample08 assisted-removal
  rounds; the unlock-radius trade-off, the diagnosed
  `white_edge_contamination` pipeline-parameter limitation, and the user
  1:1-rejection precedent for a machine-passing candidate.
- `tasks/double-marine-bed-wrapper-batch/PLAN-bg-complete-solution.md` —
  "Known from prior work" section: the flood/punch failure history and the
  chroma-regeneration rejection rationale.
- `scratchpad/transparent-gen-matrix.md` — the full model survey, including
  models ruled out by schema alone (Recraft V3, Ideogram) without a live probe.
- Drive raw outputs + `metrics.json` + edge crops:
  `.../production files/double Marine Bed Wrapper/images/Images/candidates/{bg-gen-api-v1,bg-gen-matrix-v1,bg-assisted-v2,comfyui-v1}/`
- `tasks/double-marine-bed-wrapper-batch/comfyui/REPRODUCE.md` — exact
  reproduction steps for the LayerDiffuse/BiRefNet-HR ComfyUI probe (rejected
  route, kept reproducible in case a future prompt style is worth a fair
  second look).

## Failure lessons

- **Proxy metrics lie — verify at the layer the user actually judges.** The
  flood/punch/rim removal family reported `white_rim=0` (a passing proxy)
  while directly deleting real pale painted content (ultra-pale ghosts,
  residual fringe) that the user caught on inspection. A code-gate metric that
  has never been calibrated against a real rejection case is not evidence of
  quality — it is untested. (Same shape as the pre-existing `region-iou ≠ fit
  calibration` and `code gates need calibration` wiki lessons — this is a new
  concrete instance of that pattern in the background-removal domain.)
- **A machine "PASS" is not the same actor as user acceptance.** Both image15
  and sample08 hit `machine_pass=true` at some point in the corrections
  history, and the user still rejected a machine-passing candidate on native
  1:1 inspection (a coral-fork correction widened a real gap by ~30px on each
  side — visible only at full resolution, not in the machine's per-guard
  disk sampling). The gate is a necessary filter, not a sufficient one; Stage 4
  human review is not a formality and must not be skipped or treated as
  optional once the gate passes.
- **Sparse correction guards miss "bubble-class" deletions.** Small, thin,
  low-contrast foreground features (bubble rims, thin coral fringe) are the
  class most likely to be silently deleted by an automatic proposal without
  ever tripping a guard that wasn't specifically placed on that exact feature
  — because guards are necessarily sparse (a handful of hand-placed disks),
  not a dense per-pixel oracle. The corrections stage caught these only when
  a human (or a blind statistical scan cross-checked against source pixels)
  went looking specifically for near-paper-but-tinted content, not from the
  gate alone. Any future gate expansion should treat "guard coverage of known
  defect classes" as its own audit question, not assume guard density implies
  defect-class coverage.
- **A wide correction-unlock-radius can trade one fix for a new regression.**
  `--correction-unlock-radius=110` reopened enough of a neighboring region to
  newly break a guard that had previously passed (net failure count unchanged,
  7→7, on image15). Radius should default narrow (R≈24) and only widen with a
  re-run of the full gate to confirm no new regression, never assumed safe.
- **Claim status must cite primary evidence, not prior summaries.** The
  `gpt-image-2` transparency claim flipped twice while being banked: the matrix
  lane's docs only covered the fal wrapper (no `background` param), so a
  drafting agent downgraded "rejected" to "untested" — but the orchestrator HAD
  separately probed the direct OpenAI API the same day and captured the primary
  evidence: HTTP 400, `"Transparent background is not supported for this
  model." (param: background, code: invalid_value)`, 2026-07-10. Final status:
  **rejected for transparency, probed live**. Lesson: bank a claim with its raw
  API response / measured metric attached; a status inherited from any summary
  (in either direction) is not evidence.

## Open questions

- **LayerDiffuse conv-injection variant untested.** The `layer_xl_transparent_conv`
  checkpoint (~3.6GB) was downloaded as a follow-up probe for the weak
  attention-injection alpha finding but was not confirmed run before this
  session's reporting cutoff (`tasks/double-marine-bed-wrapper-batch/comfyui/REPRODUCE.md`
  notes it as downloaded, follow-up status unclear). If a future task needs a
  local/free native-alpha generation route, this is the next thing to try
  before re-deriving the whole ComfyUI/LayerDiffuse setup from scratch.
- **PhotoRoom / Clipdrop (or other dedicated background-removal SaaS APIs)
  unprobed.** This session's Route E used Adobe (via MCP) + `vitmatte`/
  `closed_form` matting only. A dedicated commercial matting API was never
  compared against that pipeline for cost, quality, or the pale-paint-vs-paper
  ambiguity this style keeps hitting (see `white_edge_contamination` diagnosed
  limitation in `REVIEW/marine-bg-complete/INDEX.md`).
- ~~`gpt-image-2` direct API transparency~~ — RESOLVED: probed live 2026-07-10,
  API refuses with 400 `"Transparent background is not supported for this
  model."`. Closed; see Failure lessons above.
- **image15's pale/paper-adjacent fringe failure is NOT the distance
  threshold.** `--decontam-paper-distance` is now a CLI flag (default 80.0,
  byte-identical behavior when unset) and a measured sweep (30–120) showed 80
  is the local optimum — every other value is WORSE on all three failing
  probes, because the threshold is a joint condition ("pixel contaminated
  enough" AND "donor colorful enough") whose halves move oppositely. Real
  levers: search geometry (`target_radius_px=8`, `boundary_width_px=2`,
  interior-erosion depth) or decoupling the two thresholds — open decision for
  whoever owns `assisted_bg_remove.py` next.

## Rationale (why this earns a wiki entry)

Multi-session, multi-agent evidence (Codex + Claude + Cursor lineage per
`PLAN-bg-complete-solution.md`'s header) converged on a **generation-first**
architecture after repeatedly re-discovering that background-removal-after-
the-fact (flood/punch, chroma-key regeneration, naive matting) cannot cleanly
separate pale watercolor paint from paper without either destroying real
content or leaving fringe — a real, measured, cross-tool pattern, not a single
anecdote. The one specific prompt-time lever found (edge-hygiene block) is
cheap, free, and transferable to any future net-new transparent generation on
this model — worth banking so it's never re-discovered from scratch.
