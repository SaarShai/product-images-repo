# IMPROVEMENTS — running list (target ≥20, then ≥20 more)

Status: DRAFT (from self-review) → will be validated/extended by research agents A–F.
Tag: [BN=bottleneck] [src] [status: IDEA|IMPL|VERIFIED|DROPPED]

## Batch 1 (from direct experience; ranked bottleneck-first)

### Masking (B1 — the #1 bottleneck)
1. **Auto-mask from text/click** (promptable segmentation: SAM2/Grounded-SAM/lang-SAM or fal/replicate endpoint): "the taxi roof sign" → tight mask. [BN1] [agentA] [IDEA]
2. **Mask preview-gate**: always render mask-overlay + assert coverage (target px inside, expected band, area sane) BEFORE any API spend. Cheap; prevents the ~100px-off waste. [BN1] [build] [IDEA]
3. **Hardened CC auto-mask** (`cabmask.py`→general `automask_cc.py`): largest-component + region restriction + fill + IN-BAND assertion. [BN1] [build] [IDEA]
4. **Fast coord handoff**: labeled-grid generator + click-to-coords HTML widget so coords are read, never eyeballed. [BN1] [build] [IDEA]

### Verification (B2 — manual eyeballing)
5. **VLM-judge harness** (`judge.py`): (before, after, crop, rubric)→structured verdict {well-formed, style-match, leftover-text, artifacts} via Claude/GLM vision. [BN2] [agentC] [IDEA]
6. **OCR leftover-text detector**: after text removal, OCR the region, assert empty. [BN2] [agentC] [IDEA]
7. **Perceptual change-gate**: add SSIM/LPIPS/DINO cosine to the pixel gate (perceptual, not just max-delta). [BN2] [agentC] [IDEA]
8. **Style-match metric**: CLIP/DINO cosine of new element vs surrounding/style-ref → numeric adherence. [BN2] [agentC] [IDEA]

### Routing / methods (B3 + F1–F3,F8)
9. **Engine-routing dispatcher** (`edit.py`): task-type→engine (redraw-in-place=FluxFill; remove=Bria; restyle+layout=Flux.2; reshape=stretch+Kontext; consistency=ref-lock). Stops re-deriving + wrong-engine fails. [BN3] [build] [IDEA]
10. **Anti-reframe prompt templates** for Kontext/Flux.2 (preserve composition/position/scale). [agentE] [IDEA]
11. **Reliable "no text" recipe** encoded (mask+Bria or proven phrasings). [agentE/B] [IDEA]
12. **Two-pass removal** (dilate→erase→OCR-recheck→re-erase residual) as a standard routine. [agentB] [IDEA]
13. **Mask dilation defaults** tuned to prevent heal-back + edge halos. [build] [IDEA]

### Geometry (B4 + F9)
14. **ControlNet/img2img geometry fit**: SVG→lineart/canny/mask conditioning→fill contour, holes empty. [BN4] [agentD] [IDEA]
15. **SVG→conditioning toolchain** (one script: contour-mask, holes-mask, keep-clear-mask, lineart, aspect from the SVG). [BN4] [agentD/build] [IDEA]
16. **Enclosed-hole clarity check** (not region-IoU): assert cutout voids are clean/empty. [build] [IDEA]

### Throughput / cost / reliability (B5,B6)
17. **fal QUEUE + parallel/batch** (fal-client, queue.fal.run) → concurrent candidate fan-out. [BN5] [agentF] [IDEA]
18. **Idempotent cache** keyed by (image-hash, prompt, params) → never pay twice, reproducible. [agentF] [IDEA]
19. **Run manifest + deterministic seeds** → reproducibility + regression. [agentF] [IDEA]
20. **EVAL SET + runner**: fixed element-edit cases (+ stress-test SVGs) w/ expected outcomes; scores every improvement; regression guard. [BN6] [build] [IDEA]
21. **Scout-then-final**: cheap/low-res scout to pick engine/prompt, then one big final. [agentF] [IDEA]
22. **Auto reference-style packet**: extract best style crops from the same illustration to feed as refs. [agentE] [IDEA]

### Skills / process
23. **`element-edit` skill** encoding routing + auto-mask + gate + auto-judge SOP. [build] [IDEA]
24. **Local LaMa/IOPaint** FREE removal/inpaint fallback to Bria. [agentB] [IDEA]

(>=20 reached. Research agents A–F will validate, correct, and add Batch 2.)
