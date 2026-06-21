# STATUS — live tracker

## VERIFIED this session
- **#2 mask_check.py** — pre-spend mask guardrail. TEST: correct mask containment 0.998 PASS (exit0); 100px-off mask containment 0.000 FAIL (exit2). Catches the exact waste mode.
- **#1 automask.py** — text→mask via fal SAM-3. TEST: "yellow taxi car" → tight cab mask in ONE call; mask_check yellow-containment 0.857 PASS; overlay confirms cab (not buildings). #1 bottleneck (mask eyeballing) eliminated.

## Research dossiers (all 6 done) — key picks
- A automask: **fal-ai/sam-3/image** (text→mask) ✅ built. Fallback Replicate grounded_sam. Local: Florence-2→SAM2 (later).
- B removal: **IOPaint+LaMa** local/free (MPS) = best free eraser; fal Bria = paid (already working). Dilate mask ~12px pre-feather.
- C judge: **pairwise** forced-choice VLM (+25pp vs pointwise), forbid ties, swap order; GLM-4V default; OBJECTIVE-gate/AESTHETIC-advisory split; **PaddleOCR** leftover-text gate; **DINOv2 patch-cosine** leakage map; metric libs piq/lpips/ImageHash.
- D geometry: we ALREADY have svg_to_controlmap.py + controlnet_inpaint_gen.py (SD1.5) → **port to SDXL** (xinsir canny CN + sdxl-inpaint). Differential-diffusion / FLUX Fill for hero. Holes via hard mask, never prompt.
- E prompting: anti-reframe clause ("keep exact position/scale/pose; do not zoom/recenter/reframe"); positive "no text" ("surfaces blank, add no text"); prescribe medium not "keep style"; consistency via canonical ref fed back; gpt-image input_fidelity=high, first image = must-preserve.
- F ops: **fal QUEUE API + fal-client async** (parallel fan-out, ~10 concurrency, never drops); **content-addressed cache** (sha256 pixels+prompt+params, 40-90% fewer paid calls); free-local-first cascade (LaMa→Bria); per-call manifest + snapshot regression tests.

## QUEUED (prioritized: leverage × low-friction)
P1. Engine-routing dispatcher `edit.py` (encodes routing + automask + gate; one command) [#9]
P2. gencache content-addressed cache wrapper for fal calls [#18]
P3. judge.py — programmatic VLM verdict (OpenAI gpt-4o vision; well-formed/style/leftover-text/artifacts; pairwise mode) [#5,#6 folded]
P4. prompt-templates.md + bake into wrappers (anti-reframe, no-text, medium-prescribe) [#10,#11,#22]
P5. fal queue parallel fan-out in falgen/dispatcher [#17]
P6. IOPaint+LaMa free eraser wrapper + cascade [#24,#12]
P7. DINOv2 outside-mask leakage metric add to compose gate [#7]
P8. EVAL SET + runner (fixtures from real cases + stress SVGs) [#20,#19]
P9. Port controlnet_inpaint_gen.py → SDXL for exact geometry [#14,#15,#16]
P10. element-edit SKILL (SOP) [#23]

## BATCH 2 candidates (new, from research) — to expand to ≥20 more
- Two-stage mask: SAM-3 whole-object → SAM2 box-refine sub-part (sharper sub-element masks).
- Replicate as secondary provider (failover + grounded_sam cheap mask).
- Qwen-Image-Edit for TEXT edits (SOTA text render/replace).
- Differential-diffusion for seamless geometry restyle (graded change map).
- promptfoo/DeepEval wrapping confirmed-bad edits into permanent regression tests.
- ImageHash near-dup smoke test (cheap pre-filter before VLM).
- fal upload_file once, reuse url across candidates (cut base64 re-upload).
- MediaPipe finger-count (advisory) for hands.
- ComfyUI workflow-as-API to consolidate the ~6 controlnet_*_gen scripts.
- Scout-then-final low-res routing to cut cost.
- Krita-AI-diffusion architecture study (select→inpaint UX) [study only, GPLv3].
- Mask post-process standard (threshold+close+feather+dilate12) as a shared util.
