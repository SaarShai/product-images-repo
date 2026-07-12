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

For a NEW product illustration, generate real alpha from the start. The
repeatable API route is OpenAI `gpt-image-1` with
`background=transparent`; the strongest measured semantic-redraw route for an
EXISTING illustration is ChatGPT Images 2.0 in a signed-in browser. The browser
probe returned genuine RGBA and preserved the fish/coral layout better than
the API-native-alpha and `gpt-image-2`+key comparisons, but it still redrew
details. Therefore the decision splits on pixel identity: use transparent
regeneration when a semantic redraw is acceptable because it avoids the
paper-versus-pale-paint segmentation problem; use correction-led matting when
the existing raster's exact content must survive. In both cases, split RGB and
alpha before upscaling and require native-resolution four-background review.

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

2. **Existing art, semantic redraw acceptable → ChatGPT Images native alpha.**
   In a signed-in browser, upload the source and ask ChatGPT Images to recreate
   the subject/style/composition on a fully transparent true-alpha PNG, with a
   clear margin and fully closed outlines. The successful fish/coral probe
   (`REVIEW/marine-bg-complete/fish-regen/fish_APP_s1.png`) is 1024×1536 RGBA,
   alpha 0–255, exact A=0 66.7557%, layout-mask IoU 0.8427, and global SSIM
   0.7491 against the resized source. It is the strongest regeneration tested,
   but it is not pixel-identical and its metadata does not prove the backend
   model ID was `gpt-image-2`. Direct API `gpt-image-2` transparency remains a
   separate, rejected combination (HTTP 400).

3. **Upscale without corrupting alpha.**
   `tasks/double-marine-bed-wrapper-batch/alpha_aware_upscale.py --method split
   --scale 8` — RealESRGAN runs on RGB only; alpha is resized independently via
   Lanczos and recombined. Verified: alpha MAE 0 / max-error 0 vs the Lanczos
   reference, source SHA-256 unchanged. The ChatGPT Images fish result also
   passed the real full-size path: 1024×1536 → 8192×12288 RGBA, alpha MAE 0,
   max error 0, and unchanged source SHA-256. `--method direct` (undocumented native
   ncnn RGBA) and `--method two-plate` (nonlinear black/white-plate recovery,
   leaks foreground texture into alpha) are inferior — not used in production.

4. **Need a flat key color instead of alpha (same model, same call shape):**
   `background=opaque` + prompt suffix demanding a named pure color, "flat
   solid fill, no watercolor texture in background" (this last phrase was the
   effective lever vs a plain color request). Pick the key color per image —
   it must be absent from the art's own palette. Measured: 68.8% ΔE<5 to the
   model's own actual fill color, 0% edge-band spill, only 4 enclosed pockets
   — best of 3 keyable arms tried (vs Recraft V4 wrong-hue and Flux/dev
   ignoring the instruction entirely). Still requires a real despill/key
   algorithm downstream, not a one-shot perfect key.

5. **Existing image, exact pixels required → correction-led removal.**
   Adobe MCP connector's remove-background action → semantic proposal (alpha
   seed, not a final answer) → `tasks/double-marine-bed-wrapper-batch/assisted_bg_remove.py
   --backend vitmatte` (+ sparse red/blue correction strokes only where the
   proposal is visibly wrong; `--correction-unlock-radius` narrow, ~24, not
   wide) → frozen gate
   `tasks/double-marine-bed-wrapper-batch/bg-benchmark/verify_bg_solution.py`
   → **mandatory user review** of the native-resolution white/gray/black/
   magenta composite before any candidate can move to `Images/finals/`.
   `machine_pass=true` is printed as `PENDING_HUMAN_REVIEW`, not approval.
   Fresh verification of the strongest current candidates is not complete:
   image14 and sample08 pass the machine gate but remain pending human review;
   image15 fails all three frozen white-edge probes (left salmon coral, upper
   kelp, right pink coral). Do not describe Route 5 as solved for arbitrary
   white-paper watercolor originals yet.

## Evidence links

- `REVIEW/marine-bg-complete/fish-regen/fish_APP_s1.png` and
  `BOARD_fish_APP_s1.png` — genuine RGBA ChatGPT Images result and the
  white/gray/black/magenta review surface. `JUDGE_app_vs_api.png` compares the
  source, app-native-alpha result, and `gpt-image-2`+key result.
- Product candidate folder
  `Images/candidates/bg-gen-fish-regen-v1/x8-split/` — the 8192×12288 split
  RGB/alpha upscale, `metrics.json`, and four-background `review-board.png`.
- OpenAI, “Images in ChatGPT” — current product documentation states that
  ChatGPT Images 2.0 can make the background transparent:
  https://help.openai.com/en/articles/11084440-chatgpt-images-faq
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
- **App product name is not API model provenance.** ChatGPT Images 2.0 produced
  genuine RGBA, but the UI, downloaded PNG, and content URL carried no model
  identifier. Record the surface as “ChatGPT Images” because calling it
  `gpt-image-2` would contradict the separately observed API 400 and invent a
  backend fact not present in the evidence.
- **Approve one before scaling.** A previous lane generated an 18-image batch
  before the user had approved one representative candidate. The durable gate
  is: one raw candidate → machine checks → native-resolution four-background
  board → explicit user verdict → only then batch or upscale. The fish x8 run
  here is an engineering proof kept in `Images/candidates/`, not a production
  promotion.

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

## 2026-07-11 update — Route C-green chroma-key regeneration, aura/glow defect class, A2 model-routing instability

**New verified default when `gpt-image-2` must render the art:** `gpt-image-2`
still refuses `background=transparent` (HTTP 400, re-confirmed). When that
model specifically must produce the art, key against **green (`#00FF00`)**,
not magenta/blue — measured bg↔art separation is roughly 2x magenta's (ΔE
11.5 vs 6.8; azure 5.9-9), and the green background stays near-flat
(94.6-97.2% of pixels within ΔE<3 of its own sampled fill) under every prompt
style tried (`REVIEW/marine-bed-transparent/chroma-lane/chroma_gates.json`).

- **Gen:** OpenAI Responses API, **async background job**, not the sync
  `images/generations` call — sync dies at ~75s for `quality=high`
  `1024x1536`; there is no `input_fidelity` param on this surface (400 if
  added). Attach the reference image. Minimal-P1 prompt style: "solid flat
  uniform background exactly #00FF00, every bg pixel identical, no
  gradient/vignette/texture/shadow/glow; nothing cropped at the edges." Full
  prompt variants: `REVIEW/marine-bed-transparent/chroma-lane/PROMPTS.md`.
  Generator: `REVIEW/marine-bed-transparent/chroma-lane/chroma_gen.py`.
- **Key:** `scripts/chroma_key.py` — a
  global Lab ΔE two-threshold alpha (enclosed pockets die by construction).
  `DE_OPAQUE=11`, not 8 (8 leaves a visible green rim). Boundary unmix/despill
  are confined to the dilated transition band only; interior bubbles are
  untouched.
- **Upscale:** `scripts/chroma_key_upscale.py`
  — nearest-RGB refill under `alpha=0`, then Real-ESRGAN x4 on RGB, Lanczos on
  alpha, recombine. Final proof:
  `REVIEW/marine-bed-transparent/chroma-lane/final-candidate/marine_green_P1_keyed_x4.png`
  (4096x6144). Known bug: `alpha_aware_upscale.py`'s donor threshold of
  `1/255` lets unstable low-alpha RGB poison the refill — use
  `chroma_key_upscale.py` for chroma-keyed sources instead.
- **Verification:** the uniform frozen-source-mask harness
  `REVIEW/marine-bed-transparent/verify-matrix/verify_all.py`
  (`verdict.json`/`VERDICT.md`) found `chroma_key.py` the **only** method with
  0 residual green pockets AND 0 deleted art. ImageMagick/ffmpeg naive
  chroma-key left 864-1559 green pockets; plain BRIA/BiRefNet ML matting on
  the flat-green source deleted up to **18.7%** of the art (thin
  branches) — both now rejected/measured, not just suspected.
- **Better unmix/despill (advisor-reviewed, not yet in the checked-in
  script):** donor-regularized unmix `F = (α·D + λ·F0) / (α² + λ)`,
  `λ = [0.1·(1-α)]²`, instead of naive per-pixel unmix (unstable as α→0);
  despill only in OKLab chroma, never a flat green-channel clamp (damages
  true yellows); treat painted-in spill as a bounded proposal, not truth.
  Gates to keep for any future chroma-key harness: recomposition error,
  bubble ring-vs-center alpha, stratified deleted-art recall by feature
  thinness, x4-upscale hidden-RGB poison test. Source: GPT-5.6 Sol Ultra
  advisor review (session scratchpad `advisor2_reply.md`) — advisor guidance,
  not yet measured in this repo's own harness.

**New defect class — painted aura/glow.** Native-transparent gens (API and
the A2 browser route) can paint an opaque glow/wash band around the subject;
alpha stays near-binary so every alpha-based check (histogram, enclosed
pocket) passes clean while the glow is still visible. Gate:
`scripts/aura_gate.py`. Anti-aura
prompt tail (append on top of, not instead of, the edge-hygiene block):
"isolated cutout on true transparency; transparent pixels begin immediately
outside the outermost painted or inked subject contour; all pigment and
paper-grain texture remain inside the subject silhouette only; no
surrounding watercolor wash, color bloom, glow, aura, halo, rim light,
backlight, mist, vignette, drop shadow, ambient color spill, or diffuse
silhouette expansion; flat ambient lighting; preserve soft watercolor texture
inside the forms, but no pigment outside them; only a 1-2 pixel antialiased
transition at the actual art edge." Proved: eliminated the glow in
`REVIEW/marine-bed-transparent/browser-lane/marine_browser_antiaura_s1.png`
vs earlier browser gens with the defect.

**Route A2 updates.**
- **Extraction solved:** in Claude Desktop's built-in browser, fetch the
  asset blob in-page then trigger an `a[download]` click — file lands
  directly in `~/Downloads`, no base64-chunking workaround needed. Original
  asset URLs come from `backend-api/my/recent/image_gen` (estuary content
  URLs; response also carries `conversation_id`/`message_id`/`model_slug`).
  Verify alpha in-page via `OffscreenCanvas` before downloading.
- **Model-routing instability (new risk):** the web app's host-model slug
  silently determines the image backend quality. A `gpt-5-6-pro` chat
  produced style-degraded output the user rejected; the good 2026-07-07
  exemplars ran under `gpt-5-4-thinking` (retires 2026-07-23); the user's
  true-transparency exemplar ran under `gpt-5-3`. Treat web-app model routing
  as unstable — pin `?model=` and re-validate every session. This is why the
  API chroma route (C-green) is now the stable default whenever the backend
  model matters, not just a fallback.

**Process laws re-affirmed, no change:** one candidate → user visual gate →
only then batch; pixel-verify alpha immediately after every gen; machine
gates are proxies, never the arbiter; use a uniform frozen-source-mask
verifier for any removal-method comparison; generator must never be its own
verifier.

Evidence: `REVIEW/marine-bed-transparent/chroma-lane/` (gen script,
prompts, gates JSON), `REVIEW/marine-bed-transparent/chroma-lane/` (final
candidate + prompts), `REVIEW/marine-bed-transparent/verify-matrix/`
(verify_all.py, verdict.json, VERDICT.md), `REVIEW/marine-bed-transparent/browser-lane/`
(anti-aura probe), `scripts/chroma_key.py`,
`scripts/chroma_key_upscale.py`, `scripts/aura_gate.py`.
