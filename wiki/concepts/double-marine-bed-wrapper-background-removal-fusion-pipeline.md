---
schema_version: 2
title: Double Marine Bed Wrapper — Background Removal Fusion Pipeline
type: fact
domain: tools
tier: working
confidence: 0.65
created: 2026-07-08
updated: 2026-07-08
verified: 2026-07-08
sources:
  - tasks/double-marine-bed-wrapper-batch/fusion_bg_removal.py
  - tasks/double-marine-bed-wrapper-batch/fusion_batch.py
  - tasks/double-marine-bed-wrapper-batch/validate_separability_image14.py
  - tasks/double-marine-bed-wrapper-batch/defect_scan_v2.py
resource: tasks/double-marine-bed-wrapper-batch/
supersedes: []
superseded-by: []
contradicts: []
tags:
  - background-removal
  - watercolor
  - marine-illustration
  - fusion-pipeline
  - batch-processing
  - hard-alpha
  - image-processing
  - ml-matting
---

# Background

Watercolor marine illustrations on near-white/off-white backgrounds require transparent PNG delivery with **binary alpha** (no semi-transparency), **no white fringe**, and **no wrong cutouts in pale coral** elements. Standard ML matting approaches (BRIA RMBG hard180, BiRefNet general/HRSOD, PyMatting trimap) all overcut pale foreground colors, leaving white haloes or losing delicate structure.

The core challenge: **paint-white vs. paper-white is ill-posed at pixel level**. An August 2026 survey of off-the-shelf tooling found no production solver — professional workflows layer multiple models + manual visual gating. Photoshop's Remove White Matte is GUI-only and unavailable at batch scale.

## Problem Signature

- Pale coral, blush, cream washes (chroma ~5-10, luma ≥250) are indistinguishable from background by luma alone.
- Hard-threshold alpha matting walks through these layers, creating wrong cutouts.
- Soft thresholds leave white/semi-transparent halos at boundaries.

---

# Solution v1 (Works, Incomplete)

**Fusion pipeline** in `tasks/double-marine-bed-wrapper-batch/`: `fusion_bg_removal.py` + `fusion_batch.py`.

## Algorithm

1. **FloodFG**: Border-connected flood-fill through pixels with luma ≥250 ∧ chroma ≤12 (near-white, neutral).
2. **Disagreement Recovery**: Restore foreground components iff:
   - Area ≥64 pixels (size threshold).
   - Component touches any non-flooded FG (connectivity to real art).
   - (median chroma >10 ∨ luma <235) — tint coherence gate.
3. **Refinement**: erode 1 + 3 px defringe.
4. **Output**: Binary alpha PNG (no semi-transparent edges).

## Validation (2026-07-08 run)

- **18 images processed**: all binary alpha ✓, dimensions exact ✓, holes open ✓, 0 flood intrusions ✓.
- **Gate margin**: GLM-measured separability (validate_separability_image14.py) = 64 luma units between pale-art and paper; adequate safety band for this batch.

---

# v1 Failures & Defects (User-Gated Full-Res Scan)

Defect scanner: `defect_scan_v2.py` (hi-DPI crops, boundary analysis, tint coherence).

### (1) Ultra-Pale Ghost-Layer Corals (Chroma 5-10, Luma ≥250)
- **Symptom**: Flood walks through them; restore gate misses them → **wrong cutouts**.
- **Root cause**: Indistinguishable from paper white by both flood (luma threshold) and restore gate (tint too weak).
- **Requires v2 tightening**.

### (2) Residual White-Ish Edges at Pale-Wash Boundaries
- **Symptom**: 1-pixel erode insufficient; 1 px still visible after composite.
- **Root cause**: Boundary crosses pale wash zone; no hard edge exists to anchor erosion.
- **Requires contrast-adaptive boundary erode** (eat inward until median luma <245, cap 6 px).

### (3) Image15: Painted Haze Fades to Pure White
- **Symptom**: Border-connected ragged boundary; no objective pixel-level edge.
- **Root cause**: Design ambiguity — is this intentional white ground or soft wash?
- **Decision point**: Requires user gate + design variants (see below).

---

# v2 Specification (Designed, Not Yet Run)

Tighter gate + adaptive refinement:

1. **FloodFG Tightening**: Chroma ≤5 (neutral-only); reject warm/cool tints.
2. **Restore Gate Tightening**: Component tint-coherence check; median chroma >4 for pale art; reject noise-like artifacts.
3. **Contrast-Adaptive Boundary Erode**: Instead of fixed 1 px:
   - Start erode at 1 px.
   - At each step, measure median luma in the erode-ring (1 px band).
   - Stop when median luma <245 (hard boundary found).
   - Cap max erode at 6 px (don't over-erode thin strokes).
4. **Paper Model Calibration**: Sample luma + chroma from corner pixels (known-background zones) in original source image before any white-fill pass.

### Design Variants (User Decision Points)

- **Variant A** (current v1): Fixed thresholds; defect #1 unresolved.
- **Variant B** (ink-edge hole gate): Works only for enclosed pockets; fails on open-edge ghost layers.
- **Variant C** (washfull): Accept all painted wash as ground; risks larger-scale cutout errors.
- **Variant D** (smooth boundary): Use Gaussian blur + lower threshold; produces semi-transparent edges (violates binary-alpha contract).

---

# Regression Gate: Defect Scanner

`defect_scan_v2.py` is the acceptance criterion for v2:

- **Per-tile measurement** (hi-DPI crops only; never downscaled).
- **Transparent-pixel z-distance vs. BG model**: pixels should land on known paper-white, not unknown/haloed zones.
- **Boundary-ring luma** per tile: median should be sharp (luma <200 or >240, not 220–235 twilight zone).
- **CRITICAL**: BG model must derive from **original source pixels, not white-filled RGB**. Using white-filled pixels (σ=0) degenerates the statistical test.

---

# Tooling Lessons

1. **Codex sandbox path restriction**: Codex cannot write to Google Drive paths; stage in repo-local `tasks/`, copy after via user script.
2. **Codex-rescue forwarding**: Codex-rescue agent is a **one-shot URL forwarder** (no persistence between calls). Poll `codex-companion.mjs` status/result yourself; do not rely on agent-side persistence.
3. **Edge judgment**: Judge alpha edges **only at full-res / hi-DPI crop tiles**, never on downscaled contact sheets. Downsampling hallucination masks defects and produces false-pass verdicts.

---

# Next Steps

1. Run v2 on the same 18-image batch; measure defect-scanner gate margin.
2. If v2 clears all three defect classes on this set, bank the algorithm and expand to similar watercolor marine workflows.
3. If variant A/B/C/D trade-offs persist, escalate to user for design decision.
