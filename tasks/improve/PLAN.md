# PLAN — implement pipeline improvements (plan-first-execute)

## WHAT/WHY
Raise quality/efficiency/reliability of the image-editing loop. Catalog ≥20 improvements (then ≥20 more), implement bottleneck-first, VERIFY each with a concrete test, bank durable lessons. Borrow-then-build; simplify.

Non-goals: rewriting the whole harness; chasing tools that don't run on M3/our keys; "done" without a passing test.

## Confidence
- High: bottleneck ranking (masking→verify→routing→geometry→throughput); tool picks (research-verified); automask+mask_check (tested PASS/FAIL).
- Lower: install friction (PaddleOCR/DINOv2/IOPaint/fal-client), fal queue client behavior, VLM-judge reliability on watercolor → smoke-test each before relying; prefer reusing existing keys (OpenAI vision) over new installs where equivalent.

## Order (leverage × low-friction; each has a TEST gate)
- [x] #1 automask.py (fal SAM-3 text→mask) — VERIFIED
- [x] #2 mask_check.py (pre-spend guardrail) — VERIFIED
- [ ] P2 gencache.py — content-addressed cache for fal calls; TEST: 2nd identical call = cache hit, 0 API.
- [ ] P3 judge.py — programmatic VLM verdict (OpenAI gpt-4o vision): wellformed/style/leftover-text/artifacts (+pairwise); TEST: flags melted mid-taxi BAD, clean cab GOOD; detects leftover "TAXI".
- [ ] P1 edit.py — dispatcher: task-type→engine + automask + compose gate + judge, one command; TEST: redraw a cab end-to-end, gate 0, judge PASS.
- [ ] P4 prompt_templates.py — anti-reframe / no-text / medium-prescribe templates baked into wrappers; TEST: Kontext edit keeps position (no reframe) on a sample.
- [ ] P5 fal queue parallel fan-out; TEST: N candidates wall-time ≈ slowest, not sum.
- [ ] P6 IOPaint+LaMa free eraser wrapper + cascade (free→paid); TEST: removes mid taxi locally, gate clean.
- [ ] P7 DINOv2 outside-mask leakage metric in compose gate; TEST: flags a whole-crop-repaint that pixel-gate-near-seam misses.
- [ ] P8 eval set + runner (real fixtures + stress SVGs); TEST: runner scores all gates green on known-good, red on known-bad.
- [ ] P9 port controlnet_inpaint_gen.py → SDXL (exact geometry); TEST: region-IoU ~1.0, holes empty, style acceptable.
- [ ] P10 element-edit SKILL (SOP) — encodes the above flow.
- [ ] Batch 2 (≥20 more): see STATUS.md candidates; expand + same treatment.

## done means
1. ≥20 improvements cataloged + research-backed. (IMPROVEMENTS.md + research/A–F) ✅
2. Bottleneck items implemented, EACH verified by a quoted passing test.
3. Durable improvements banked to .claude memory.
4. A second batch of ≥20 found + implemented/verified.
5. No "done" without a passing test; user tells me when to stop.
