# Defect-detector battery — draft spec v0 (Fable, pre-advisor)

Purpose: agents are blind to halos/holes; every user-visible defect class gets a
MEASURED detector a weak model can run + read. All detectors emit JSON
{metric, threshold, pass, crop_paths[]} and save 1:1 evidence crops (hi-DPI,
memory: judge-needs-hidpi-crops). Judged composites: black + panel-dark +
magenta — never white-only (memory: dehalo-gate-mandatory).

## D1 halo_gate — bright/semi-transparent edge halo
- Composite over black. Edge band = dilate(alpha>127, r=3) ∧ ¬(alpha>127).
  Inner ref band = (alpha>127) ∧ ¬erode(alpha>127, r=5).
- Metrics: (a) mean L* of edge band residual (should be ~0 over black if alpha
  honest); (b) 99th-pct L* of edge band; (c) bright-run max length along boundary.
- Fail: edge-band 99pct L* > calibrated τ. Calibrate on known-bad clarity-halo
  files + known-good chroma-keyed final.

## D2 soft_alpha_fringe — semi-transparent matte line
- soft px (0<a<255) count / boundary perimeter px. Honest AA ≈ 1–2 px per
  boundary px. > τ (≈3) = fringe. Also alpha-gradient transition-width histogram.
- For PRINT route (binarized alpha): conformance = soft% == 0 exactly.

## D3 pocket_gate — trapped background
- Enclosed alpha==0 components not touching border: count + total area + max area.
  (Exists inline in skill; promote to script.) Per-class allowance: few small
  topology-real gaps OK; flag list with crops for human.

## D4 aura_gate — painted opaque glow (RGB defect, alpha-blind)
- Existing scripts/aura_gate.py. Keep; add crops output.

## D5 hole_gate — removal ate real art (needs SOURCE)
- Input: pre-key source (white or green bg) + keyed RGBA. Paint-vs-paper
  classifier on source (ΔE from bg color) → expected FG mask; compare vs
  delivered alpha; deleted-art = expectedFG ∧ (alpha==0). Stratify recall by
  component thinness (distance-transform max). Report worst components + crops.

## D6 spill_gate — key-color contamination
- Edge band OKLab chroma vector vs interior reference; green/magenta shift Δ
  above τ = despill failure. Recomposition error over original bg as secondary.

## D7 border_gate — canvas-edge crop
- 3px border-strip alpha occupancy > 0 = fail (memory: never-crop-canvas-edges).

## D8 alpha_sanity — degenerate alpha / fake checkerboard
- Histogram (min/max/unique/zero%/soft%/opaque%); reject flat alpha; detect
  checkerboard periodicity in RGB where alpha==255 (browser-gen failure mode).

## Print-route acceptance profile (Illustrator print layer, spot-white under)
- D2 conformance soft%==0 (binary alpha), D1/D3/D4/D6/D7 pass, D5 recall ≥
  calibrated floor. Resolution floor: ≥300dpi at physical panel size — compute
  from panel dims; jaggy amplitude ≤1px ⇒ ≤0.085mm @300dpi ⇒ invisible.
- Spot-white underlay: generate choked white plate = erode(alpha_binary, choke_px)
  — choke hides underbase peeking at edges (standard underbase trapping).
  choke_px from printer registration tolerance (ask user/print shop; default 1-2px at 300dpi).

## Calibration law (memory: code-gates-need-calibration)
Every τ calibrated on ≥1 known-bad AND ≥2 known-good BEFORE trusting; gates are
advisory until calibrated; VLM/human arbitrates disagreements.
