# Whole-Panel Illustration Workflow — Plan & Blueprint (v0.1, draft for review)

Status: **PLAN ONLY**. Nothing here is built yet. Each step below is designed to be
built and verified one at a time, with your sign-off, before the next.

Date: 2026-06-20 · Machine: Apple M3 Max, 48GB unified RAM, macOS · Author: orchestrated
research (8-agent local recon + 11-stream external research, each stream adversarially verified).

> **Decisions locked (2026-06-20, user) — these supersede the conditional notes in §2/§10/§11:**
> 1. **Licensing is NOT a consideration** — Flux's non-commercial license is irrelevant. The Flux
>    quality path (FLUX.1 Fill/ControlNet/Redux, klein) is fully on the table where it helps. SDXL +
>    Xinsir union ControlNet remains the **default** spine only because it's the proven 0.969 path and
>    runs comfortably in 48GB — not for license reasons. (Pre-mortem P1 is void.)
> 2. **Start with B0 (judge-first).** Build the 3-layer vision gate + anchored test set before anything else.
> 3. **Structure-lock on the existing diffusers SDXL path** (bump diffusers ≥0.32, wire rim-split) — lowest risk, already on this machine.
> 4. **Probe Photoshop scriptability now** — confirm whether partner-model (Nano/Flux) gen-fill is batchPlay-selectable; automate if yes, fall back if no.
> 5. **Still needed from user:** canonical *good vs bad* example outputs to anchor the B0 judge rubric (req 18).

> This blueprint **builds on** the existing `svg-geometry-style-illustration` /
> `svg-template-illustration` / `skyline-template-illustration` skills and the ~50
> scripts already in `scripts/`. It does not replace them — it makes the geometry and
> styling stages **more granular, more reliable, and partly automated**, and it closes the
> one problem the records say is still open: *exact geometry AND gorgeous painted style at
> the same time.*

---

## 0. What we already know (grounded, not theoretical)

Measured in this repo (do not re-derive):

| Fact | Evidence |
|---|---|
| Pure subscription models **drift** on exact SVG coords | gpt-image best-of-6 = 0.483 white-IoU; Nano Banana richest style (5/5) but worst geometry; **no pure-gen model hits ≥0.85 region-IoU at exact coords** |
| **Local SDXL + lineart ControlNet = 0.969 region-IoU** (best geometry to date) | dreamshaper-8 + lineart CN, diffusers/MPS, on *this* machine |
| Re-seat composite = 0.863 but **degrades style** | user: "raw was good, you ruined it with exact.png" |
| Geometry metric **lies** | region-IoU 0.8x is a *visible miss* (user corrected 3×) → vision inspection mandatory |
| Gates | region-IoU ≥ 0.85 · painted_frac ≤ 0.03/hole · outside_frac ≤ 0.02 |
| Subscription CLIs **cannot do masked inpaint** | the missing capability the whole hybrid is meant to add |
| Faces/hands **open** | princess A2 fairy, 5 repair lanes unconverged |

Machine reality (checked 2026-06-20): Photoshop 2026 **+** Beta installed · `codex` + `agy`
live · ComfyUI present but **no checkpoints** (never provisioned) · Draw Things / mflux **not
installed** · diffusers **0.27.2** (needs ≥0.32 for `apply_overlay`) · torch 2.8 MPS ✓ · no Topaz.

User decisions locked (2026-06-20): **(1)** hybrid backend = keep subscription creative
engines **+ add local control**; **(2)** acceptance = **geometry-exact then quality**,
automated gate + user sign-off; **(3)** Photoshop = **automate with manual fallback**;
**(4)** geometry is #1 priority; **skylines very common**; subject content varies per job
(panels, people, etc.); faces/hands in scope.

---

## 1. North-star architecture

The entire field (verified across 11 research streams) converges on **one** answer to our
central problem, and it is *not* "find a better generator." It is:

> **Split the job across models in an img2img chain, and lock geometry by CONSTRUCTION
> (mask + pixel-space composite) — never by hoping a generator paints the right coordinates.**

### 1.1 The 3-stage spine

```
  A. STYLE DONOR            B. STRUCTURE-LOCK              C. DETAIL / FINISH
  ─────────────────         ─────────────────────         ───────────────────
  subscription engine  →    local SDXL + ControlNet   →   tile-ControlNet upscale
  (Nano Banana Pro =        (lineart/MLSD/canny             (structure-preserving,
   best style;              rasterized COORD-TRUE           low denoise) + targeted
   GPT-image = best         from the SVG) takes the         detail repair (faces/
   img2img edit)            donor as img2img init,          hands) + optional
                            re-imposes the exact            Photoshop / Topaz polish
  generate N raws,          contour; aperture/rim-
  reward-rank for style     split inpaint locks the
  (HPSv3), keep best 1–2    cutouts by construction
                            + PIXEL-SPACE composite
```

- **A** is what we already do well (rich style, geometry drift — that's fine, it's a donor).
- **B** is the lever that's *coded but unbenchmarked* (`rimsplit_inpaint_gen.py`) and already
  reached **0.969** in its simpler form. This is where the build pays off.
- **C** only *enhances* — and must re-pass the geometry gate after, because tile-upscale
  drift is real (it is **not** "structure-preserving by construction" — it's denoise-dependent).

Each arrow is a **gate**: region-IoU / white-IoU / outside_frac + vision. A handoff that
fails the gate routes back (see §8 restart router), it does not silently proceed.

### 1.2 Five laws (cross-cutting, non-negotiable)

1. **Geometry comes from the SVG, rasterized coordinate-true** (`svg_to_controlmap.py`) — never
   edge-detected from a render. (This is *why* 0.969 happened.)
2. **The aperture guarantee is a pixel-space composite**, not the sampler. Latent masking
   leaks and color-shifts (PELC, arXiv 2512.05198, Dec 2025). Always `apply_overlay` the exact
   cutout interiors back after generation.
3. **Reference IMAGES, never prose**, for style (repo HARD RULE; every stream re-confirmed it).
4. **The geometry metric is the only non-gameable oracle.** Reward models and VLM judges
   measure *zero* geometry — they rank style only; region-IoU/white-IoU stays the hard gate.
5. **Never ruin a good raw.** The loop keeps the best-so-far as a checkpoint with a
   non-regression guard (this is "peak retention" in Generation Navigator, and our existing memory).

---

## 2. Backend matrix (the hybrid, decision 1)

| Backend | Role | Feasible here? | Use when |
|---|---|---|---|
| **subgen.py → codex (OpenAI image-2)** | Style donor; best img2img/composition-preserving edit | ✓ live | Stage A donor; mid-point feed-back edits |
| **subgen.py → agy (Nano Banana Pro/2)** | Style donor; richest watercolor vocab | ✓ live (429 quota) | Stage A donor (best style) |
| **Local diffusers SDXL + Xinsir union ControlNet** | **Structure-lock (Stage B)**; the geometry engine | ✓ proven 0.969 (bump diffusers ≥0.32) | Every geometry-critical lock; commercial-safe |
| **Draw Things** (app + `draw-things-cli` + gRPC + JS scripting + MCP) | One backend that does masked-inpaint **+** ControlNet **+** IP-Adapter **+** Flux Fill **+** Qwen-Edit — the pieces codex/agy lack; sidesteps the diffusers fp16-MPS IP-Adapter bug | ⚠ **not installed** (Apple-Silicon-native, low-mem) | Strong candidate for the automated local inpaint/style backend — **spike first** |
| **mflux** (MLX CLI) | Flux Fill/Canny/Depth/Redux, MLX-native | ⚠ not installed; ControlNet **canny-only** | High-volume drafts; Flux Fill rim-paint |
| **ComfyUI on MPS** | Heavy/experimental graphs (multi-ControlNet, BrushNet, pose) | ⚠ present, **no checkpoints** | Hardest skyline/character cases only; pattern-mining bench |
| **Photoshop 27 partner-model Generative Fill** (Nano Banana / FLUX, via UXP `.psjs`) | TRUE masked inpaint with the user's best style engines | ✓ PS installed; **GUI-foreground only**, batchPlay model-select **unconfirmed** | Hero-quality section fill; manual fallback (decision 3) |
| **Firefly Services Fill API** | Headless masked inpaint | paid; **Firefly models only** (no Nano/Flux) | Headless throughput when style ceiling OK |
| **Scenario** ($45/mo) | Managed ControlNet+inpaint+IP-Adapter+Flux-LoRA in one call | SaaS | Fast alternative to fixing local ComfyUI; benchmark vs 0.969 first |
| **fal.ai / Replicate** | FLUX ControlNet+inpaint, pay-per-call (no floor) | SaaS | Cheaper than Scenario for spot calls |
| **Recraft V4 Vector** | Net-new **SVG** from spec + brand-style | SaaS | Reference-SVG generation only (not geometry engine) |
| **Magnific Precision / Freepik / Topaz** | Structure-preserving upscale/relight | SaaS / app | Stage C finisher only, after gate + sign-off |

**Recommended default spine on this Mac:** subscription donor (A) → **local SDXL + Xinsir
union ControlNet** structure-lock (B) → **xinsir tile-SDXL** upscale (C), with **Draw Things**
spiked as the automated inpaint/IP-Adapter backend and **Photoshop** as the hero/fallback fill.

> ⚠ **Licensing flag (decision needed — see §11).** FLUX.1-dev, Shakker Union, Alimama inpaint
> are **non-commercial** licenses. If these product images ship commercially, the Flux control/fill
> spine is **legally blocked**; only FLUX-schnell / FLUX.2-klein-4B (Apache-2.0) and the **SDXL +
> Xinsir** path are commercial-safe. The SDXL path is also our proven 0.969 path — so this is both
> the safe and the strong default. Flux stays an *optional* quality experiment pending the license call.

---

## 3. The granular GEOMETRY stage

Decomposed from today's coarse "parse SVG → outset → contract base" into reliable sub-steps,
each with a tool and a gate.

| # | Sub-step | Tool (exists / NEW) | Gate |
|---|---|---|---|
| G1 | Parse SVG → roles (contour, cutouts, sockets, keep-clear, no-focal) | `svg_geometry.py` + `svg_classify.py` (exist) | manifest non-draft, contours non-empty |
| G2 | Outset cutouts to absorb drift | `outset_cutouts.py` (exist, default 30) | openings stay separate |
| G3 | Build coordinate-true **control maps** (lineart **+** MLSD for straight lines **+** depth/normal for relief) | `svg_to_controlmap.py` (exist) **+ NEW `build_control_assets.py`** (controlnet_aux + Depth-Anything-V2) | maps share exact viewBox→canvas registration |
| G4 | Build **region/zone masks** (per skyline panel / control cluster / keep-clear) | **NEW** from `svg_classify` regions | one mask per zone |
| G5 | (skylines) **Allocate** landmarks/run-through/arch to zones | `skyline-template-illustration` (formalize the planner — currently narrative) | one landmark per physical panel |
| G6 | Structure-lock generate: SDXL + union ControlNet, scale ≈0.8–1.0, `start=0`, `end≈0.7–0.85` | `controlnet_*` (exist, **upgrade**) | region-IoU ≥ 0.85 |
| G7 | **Aperture/rim-split lock**: soft mask (hard-0 over cutouts, ramped rim) + **pixel-space `apply_overlay`** of exact aperture interiors | **`rimsplit_inpaint_gen.py` (exists — upgrade to Differential-Diffusion mask + apply_overlay; swap base to BrushNet frozen painterly branch)** | white-IoU clean; no rim seam |
| G8 | Measure + overlay | `geom_iou.py`, `svg_geometry_check.py`, `judge_prep.sh` (exist) | all three gates |

**Conditioning choice (settled):** MLSD = skylines/control-panels (straight lines), canny/lineart =
die-cut contour, lineart/softedge + depth = characters. Multi-ControlNet for mixed cases (heavy on
MPS — budget it).

**Soft layout methods (GLIGEN boxes, regional-attention) are for G4/G5 coarse "what goes where"
ONLY** — they cannot pin a 1-px edge; the construction lock (G7) is the sole arbiter of exact edges.
Note GLIGEN is **SD1.5-family only** (matches our 0.969 dreamshaper-8 base — coherent, but caps style
ceiling).

---

## 4. The granular STYLE stage

| # | Sub-step | Tool | Gate |
|---|---|---|---|
| S1 | Build style packet from reference IMAGES (full + region/edge/texture/component crops) | `build_reference_style_packet.py` (exist) | packet has edge-treatment crops |
| S2 | **Style-packet quality gate** (currently missing) | **NEW** heuristic + vision check | packet strong enough or regenerate |
| S3 | Style donor: N raws via subscription (Nano best style / GPT-image best edit) | `subgen.py` (exist) | — |
| S4 | **Reward-rank** donors (HPSv3 default; ImageReward/PickScore) | **NEW `score_candidates.py`** | shortlist top 1–2 (style only) |
| S5 | Carry style into the locked geometry: img2img-init donor into Stage-B (MPS-safe), **or** IP-Adapter/Redux **in Draw Things** (avoids diffusers fp16-MPS bug), **or** per-region IP-Adapter for zone styles | Draw Things / diffusers | style_score (VLM) |
| S6 | Regional restyle / "feed mid-point back as reference" | Qwen-Image-Edit / Flux Kontext (Draw Things) — **downstream of geometry only**, then re-assert aperture + re-gate | region-IoU unchanged |

**Why this order:** style is the *donor and the finisher*; geometry is locked *in between*.
This is the inversion that makes "exact geometry AND great style" achievable — the style never has
to hit coordinates, and the geometry never has to invent style.

---

## 5. Section/detail repair + faces, hands, feet (req 2, 4, 8)

**Doctrine:** detect → crop → targeted-inpaint (low denoise 0.35–0.45) → recomposite. **Never run a
full model on the whole 1:3.4 panel to fix a hand.** This formalizes the repo's manual
fanout-SYNTHESIS pattern.

Tiered ladder (escalate per-crop only when the cheaper tier's quality fails):

1. **Local SD1.5 detailer** — YOLO (`face_yolov8`/`hand_yolov8`) detect → crop → ControlNet inpaint.
   For hands: **MeshGraphormer HandRefiner** + `control_sd15_inpaint_depth_hand` (strength 0.4–0.8),
   preserves pose while fixing fingers. *Same SD1.5+ControlNet stack already proven here.*
2. **Flux Fill crop** (Draw Things / mflux GGUF Q6) — when SD1.5 watercolor quality undershoots.
3. **Photoshop partner-model generative fill** (UXP-automated, Nano/Flux) — hardest crops + sign-off.
4. **Subscription crop redraw** (codex/agy on the *small* crop — drift is bounded) — a $0 tier.

**Traps:** CodeFormer/GFPGAN/RestoreFormer **destroy watercolor** (photoreal hallucination) — do not
use on non-photoreal characters. Recomposite needs feathered-alpha + color-match (Poisson/seamless)
or the crop seams in watercolor — the loop must handle blend explicitly.

New tool: **`scripts/region_detailer.py`** (reuses `controlnet_inpaint_gen.py`; YOLO bbox → feather
mask → crop inpaint → composite back → geom gate + vision judge).

---

## 6. Reference-asset generation (req 3, 6, 10)

> "Reference input beats text" — operationalized as a **conditioning-asset factory**.

- **`build_control_assets.py` (NEW):** given the SVG and/or a reference image, emit the stack:
  coordinate-true lineart (existing) **+** depth (Depth-Anything-V2 CoreML/MPS) **+** normal **+**
  softedge **+** (characters) openpose/dwpose — via `controlnet_aux` (standalone pip, no ComfyUI).
  Lineart stays highest control-weight = geometry; depth/normal lower = relief, never override contour.
- **Region/layout assets:** per-zone masks from `svg_classify` → GLIGEN boxes ("what goes where") +
  regional IP-Adapter ("which style where"). This is the skyline-allocation problem, made mechanical.
- **Net-new SVG from a spec:** **Recraft V4 Vector** (real editable paths) → normalize with
  vtracer/potrace/Inkscape CLI → **must pass the same geom gate** (it's a draft, not authoritative).
- **Mid-point feedback:** any accepted intermediate raw becomes a reference image / img2img init for
  the next targeted pass (style continuity via Kontext/Qwen-Edit, geometry re-locked after).

---

## 7. The high-DPI vision judge (req 5)

A **3-layer fusion gate** (replaces "metric or eyeball"):

- **L1 — geometry oracle (hard, non-gameable):** `geom_iou.py` region-IoU ≥ 0.85 + white-IoU
  (hole clean) + outside_frac (no bleed). Pure calc. Gate everything behind this first.
- **L2 — defect flags (cheap):** MediaPipe (faces/hands) + a structure/edge-alignment check vs the
  SVG (for the common skyline case where MediaPipe is irrelevant) + pyiqa artifact flags.
- **L3 — VLM-as-judge (style/anatomy, NEVER geometry):** a rubric VLM reads the **overlay + zoomed
  high-DPI crops**, cross-provider (2 models, swap order), **rubric anchored to pinned pass/fail gold
  examples**, **multi-sample/self-consistency** to cut noise, randomized order to kill position bias.
  Records **calc-vs-VLM disagreement** as a finding (don't average it away).

VLM judges style and reads the geometry *overlay* — it never scores geometry from the raw image
(unreliable). New: **`scripts/vision_judge.py`** wrapping `judge_prep.sh` + crop-emitter + VLM. Cheap
L1/L2 screen → escalate to L3 only on survivors (subscription VLM calls are rate-limited).

---

## 8. Orchestration — best-of-N, "snap out of it", fleets (req 8, 13, 14, 16)

### 8.1 Typed, region-localized failure report (replaces bare IoU)
Extend the gate output to `{failure_enum, bbox, suggested_fix}` —
`spills_outside_contour | hole_not_clean | style_mismatch | face_distorted | …`. This is what lets
the router choose **Refine (region edit)** vs **Regenerate (full restart)** and what feeds
`region_detailer.py`. (ImageDoctor / OmniVerifier contract.)

### 8.2 The restart router (the "snap out of it" gate — the named missing piece)
`loop_run_monitor.py` already **detects** STUCK (S1 same-cmd 3×, S2 same-error 2×, S3 metric-stall
2×) but does nothing. Add **`restart_router.py`**: STUCK → `{Refine | Regenerate | Stop}`
(Generation Navigator pattern). **Regenerate = forced-entropy, structurally-different hypothesis** —
switch the *arm*: provider (nano↔gpt-image↔local-CN), method (ControlNet↔rim-split↔Photoshop-fill),
or seed batch. **Peak-retention:** always hold the best-so-far raw; never regress it. Cap total
restarts → emit a **human decision-brief** at the cap (don't loop forever).

### 8.3 Method-bandit fan-out (loop-engineering, per step)
Wrap `genbatch.sh` fan-out with a small **method-bandit** (arms = nano / gpt-image / local-CN /
rim-split), reward = region-IoU, **per-arm cost/quota** as a constraint, **change-point reset** on a
detected plateau. Fan in to a tournament gate (region-IoU + VLM style) → user sign-off.
- **Do NOT** let an LLM be the bandit controller (LLMs over-exploit — proven).
- **Do NOT** import LangGraph/heavy frameworks — `genbatch.sh` + `results_db.py` already do
  fan-out/fan-in/reconcile-from-disk; borrow the *pattern*, not the dependency.
- Reward models rank style only — **never** let a high-aesthetic-but-misplaced donor auto-advance
  past the geometry gate.

### 8.4 Per-step fleets
Each independent sub-task fans out subagents: N style donors in parallel (A), N seeds/methods for the
lock (B), per-zone allocation scouts (G5), per-crop detailers (§5), cross-provider judges (L3). All
under the existing supervision rules (own pgroup via `genbatch.sh`, results-collection gate, review
ALL candidates not a sample).

---

## 9. Tools & skills we build for ourselves (req 15)

New scripts (each small, each reuses the existing eval stack):
- `build_control_assets.py` — conditioning-asset factory (G3/§6).
- `region_detailer.py` — detect→crop→inpaint→composite face/hand/section repair (§5).
- `score_candidates.py` — reward-rank best-of-N style donors (S4/8.3).
- `vision_judge.py` — 3-layer fusion judge wrapper (§7).
- `restart_router.py` — STUCK → Refine/Regenerate/Stop with peak-retention (§8.2).
- `localinpaint.py` — hardened Draw Things / mflux masked-inpaint driver, subgen.py-style (§2).
- `ps_genfill.psjs` — UXP Photoshop generative-fill on a script-built mask (§2, decision 3).
- Upgrade `rimsplit_inpaint_gen.py` — Differential-Diffusion mask + `apply_overlay` + BrushNet base.

New / upgraded skills:
- **`whole-panel-illustration`** — the master orchestrator skill that subsumes geometry + style +
  repair + judge + restart (today there is no unified one; the records flag this gap explicitly).
- Formalize **`skyline-template-illustration`** planner (allocation algorithm, not narrative).
- A **`section-repair`** skill (faces/hands ladder + recomposite blend).

### Build-phase environment actions (one-time)
- Bump diffusers in the ControlNet env to ≥0.32 (for `apply_overlay`).
- Provision ComfyUI checkpoints OR install Draw Things (the spike decides which).
- Install `controlnet_aux`, Depth-Anything-V2 (CoreML), ultralytics YOLO detail models, HandRefiner.
- (optional) Draw Things + mflux; (optional) Topaz.

---

## 10. Pre-mortem — how this fails, and the guard (req: pre-mortem)

| # | Failure mode | Likelihood | Guard built into the plan |
|---|---|---|---|
| P1 | **Commercial license blocker** — Flux spine illegal for sold product images | High if commercial | Default to SDXL+Xinsir (commercial-safe **and** the 0.969 path); Flux opt-in pending §11 answer |
| P2 | **Latent mask leaks** → aperture not pixel-exact | High without guard | Mandatory pixel-space `apply_overlay`; white-IoU gate every pass (Law 2) |
| P3 | **Metric passes, eye fails** (region-IoU 0.8x looks fine, is a miss) | High | L1 hard gate + L3 VLM over overlay + record calc-vs-eye disagreement (§7) |
| P4 | **MPS too slow** (minutes/image; multi-ControlNet worse) | Medium | Crop for detail; reward-rank pre-filter so heavy lock runs on 1–2 donors; cap retries by budget |
| P5 | **Tile-upscale drifts the cutout edge** (C undoes B) | Medium | Low denoise + re-run geom gate AFTER C, not just before (§1.1) |
| P6 | **Reward/VLM gaming** — loop optimizes the judge, not geometry | Medium | region-IoU is the non-gameable oracle; reward ranks style only (Law 4) |
| P7 | **Photoshop partner-fill not scriptable** (batchPlay model-select unconfirmed; Nano-in-PS edge-shift bug) | Medium | Probe with Record-Action before betting; hard composite covers edge-shift; Firefly Fill API or local inpaint as headless fallback |
| P8 | **Draw Things scripting can't load per-opening masks headless** | Medium | Spike one panel + one skyline + one character before committing the backend |
| P9 | **Recomposite seams** in watercolor (crop blends visibly) | Medium | Feather-alpha + color-match/Poisson; vision-inspect every composite |
| P10 | **Restart router itself loops** / premature restart discards a converging trajectory | Medium | Restart budget cap + human decision-brief; calibrate S1/S2/S3 thresholds (change-point false-alarm) |
| P11 | **Getting stuck "fixing" instead of restarting** (the historic big problem) | High historically | §8.2 router makes Regenerate a first-class typed action with forced-entropy arm-switch |
| P12 | **Results not collected / silent batch death** | Medium | Existing guards: `genbatch.sh` pgroup, `sync_results_images.py --check`, Stop-hook reconcile, artifact_guard |
| P13 | **48GB RAM ceiling** on SDXL+ControlNet (+Flux) | Low–Med | SDXL fits 48GB; keep Flux crop-only/GGUF; monitor MPS OOM |

---

## 11. Open decisions for you (before/while we build)

1. **Commercial use? (load-bearing)** Will these illustrations be **sold / used commercially**? If
   yes → we default to the SDXL+Xinsir local path (safe **and** proven 0.969) and treat Flux as an
   optional non-commercial experiment only. If no / internal → Flux ceiling is open.
2. **First local backend to spike:** (a) **Draw Things** (one backend for inpaint+ControlNet+IP-Adapter,
   needs install) vs (b) **upgrade the existing diffusers SDXL path** (already 0.969, just bump
   diffusers + wire rim-split) vs (c) **stand up Scenario** ($45/mo, skip local infra). Recommendation:
   **(b) first** (lowest risk, proven), Draw Things spike in parallel.
3. **Photoshop automation depth now:** probe whether partner-model gen-fill is batchPlay-scriptable
   this week, or keep PS as manual-fallback for v1 and automate later?
4. **Example anchors (req 18):** point me at your **canonical good vs bad** outputs (e.g.
   `tasks/top-temp-workflow-test` redraws you called "beautiful", the np01 winners, the princess A2
   target) so the vision-judge rubric and style packets are anchored to *your* taste, not generic.
5. **Build order:** do you want to start with the **structure-lock (Stage B / rim-split)** increment
   (highest leverage, closes the open problem) — my recommendation — or the **vision-judge** increment
   (so every later step is measurable first)?

---

## 12. Proposed BUILD order (each step independently verified with you)

Low-risk-first, every increment ends in a gate you sign off before the next:

- **B0 — Bench harness & judge first.** Bump diffusers; wire `vision_judge.py` (L1+L2+L3) + a tiny
  fixed test set (1 panel, 1 skyline, 1 character) with *your* good/bad anchors. **Done = the gate
  reproduces your eye on known examples.**
- **B1 — Structure-lock (the open problem).** Upgrade `rimsplit_inpaint_gen.py` (Differential-Diffusion
  mask + `apply_overlay` + BrushNet base) on the test panel. **Done = exact aperture (white-IoU clean)
  AND painted rim, beating 0.863 re-seat without the style loss.**
- **B2 — 3-stage chain.** Wire donor → lock → tile-upscale with `score_candidates.py` reward-rank.
  **Done = one panel through the full chain passes gate + your sign-off.**
- **B3 — Section/face/hand repair.** `region_detailer.py` + HandRefiner on the princess A2 hand.
  **Done = A2 fingers fixed, scene preserved, you accept.**
- **B4 — Restart router + method-bandit.** `restart_router.py` on top of `loop_run_monitor.py`.
  **Done = a deliberately-stuck run snaps to a different arm instead of repeating.**
- **B5 — Reference-asset factory + skyline planner.** `build_control_assets.py` + formalized
  allocation. **Done = a new skyline from a roster runs end-to-end.**
- **B6 — Backend spikes (parallel, opt-in):** Draw Things headless mask test; Photoshop UXP gen-fill
  probe. **Done = each either promoted to a backend or shelved with evidence.**
- **B7 — Master skill.** Fold B0–B6 into the `whole-panel-illustration` orchestrator skill.

---

### Appendix — key external sources (verified 2026)
ComfyUI/MPS · Draw Things CLI+gRPC+JS (drawthings.ai, GPLv3 2026-05) · Xinsir controlnet-union-promax
(HF) · Differential Diffusion (arXiv 2306.00950, CGF 2025) · PELC "Your Latent Mask is Wrong" (arXiv
2512.05198) · BrushNet (ECCV 2024) · diffusers `apply_overlay`/`padding_mask_crop` (≥0.32) · ADetailer
+ ultralytics YOLO · HandRefiner/MeshGraphormer (ACM MM 2024) · controlnet_aux + Depth-Anything-V2
CoreML · HPSv3 (ICCV 2025) / ImageReward / PickScore · xinsir tile-sdxl · Generation Navigator (arXiv
2605.17969) · ImageDoctor (arXiv 2510.01010) · OmniVerifier (arXiv 2510.13804, ICLR 2026) · Photoshop
27 partner-model Generative Fill (Adobe helpx, Oct 2025) · Firefly Services Fill API · Scenario
ControlNet+Inpaint+IPAdapter endpoint · Recraft V4 Vector · Magnific Precision.
