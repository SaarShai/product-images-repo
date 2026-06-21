# PROGRESS log (autonomous run)

## VERIFIED & shipped (with test evidence)
| # | improvement | tool | test result |
|---|---|---|---|
| 1 | auto-mask from text | scripts/automask.py | "yellow taxi"→mask 1 call, containment 0.857 PASS |
| 2 | pre-spend mask guardrail | scripts/mask_check.py | good 0.998 PASS(exit0) / 100px-off 0.000 FAIL(exit2) |
| 18 | content-addressed cache | scripts/gencache.py | 2nd call cache-hit 0 API (8.5s→0.14s), identical |
| 5/6 | VLM judge (text+pairwise) | scripts/judge.py | TAXI→leftover_text true / erased false; pairwise picks clean, consistent |
| 10/11 | edit prompt templates | scripts/prompt_templates.py | self-test: all carry anti-reframe+no-text+medium |
| 9 (P1) | one-command dispatcher | scripts/edit.py | remove right taxi end-to-end: gate 0, judge clean, RESULT SUCCESS; overlay confirms |
| 17 (P5) | fal queue parallel | scripts/falbatch.py | 3 calls concurrent 5.11s vs seq 11.59s = 2.27x (agent J) |
| 20 (P8) | eval/regression runner | scripts/eval_runner.py | 3/3 ALL GREEN (exit0) |
| 23 (P10) | element-edit skill SOP | skills/element-edit/SKILL.md | written, references all verified tools |

## RUNNING (background agents)
- G: local LaMa free eraser (IOPaint) → tasks/improve/research/G-lama-impl.md
- I: DINOv2/LPIPS outside-mask leakage metric → I-leak-impl.md
- H: SDXL ControlNet exact-geometry (port SD1.5→SDXL) → H-sdxl-cn-impl.md

## Memories banked
auto-mask-and-guardrail.md, auto-verify-judge.md (+ earlier element-edit-diffmask-composite, image-edit-engine-routing sharpenings)

## NEXT (Batch 2, ≥20 more) — to build/verify
ImageHash near-dup prefilter · scout-then-final low-res routing · two-stage mask (SAM3→SAM2 refine) ·
Qwen-edit for text · differential-diffusion geometry · promptfoo regression wrap · MediaPipe finger-count (advisory) ·
ComfyUI workflow-as-API consolidation · Replicate failover provider · reference-style-packet auto-builder ·
PaddleOCR deterministic text gate (complement judge) · style-match DINO metric · run manifest/provenance ·
mask post-process shared util · keep-clear/hole emptiness check · cost-aware engine cascade (free-first) · ...
