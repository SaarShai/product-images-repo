# ViTMatte-S image 14 feasibility scout

Status before run: one fixed scout is authorized; this is not a final remover.

The native 941x1672 RGB source is passed to the official cached
`hustvl/vitmatte-small-composition-1k` model. An existing rejected x4 candidate
alpha is explicitly area-downsampled and converted to a conservative trimap.
That trimap is **not ground truth**. The model processor pads the native image to
a divisor of 32; it does not resize it. No output-alpha thresholding is used.

Two straight-RGBA files will share the exact model alpha: one retains source
RGB; the other uses `pymatting.estimate_foreground_ml` to estimate unblended
foreground RGB. Four native-coordinate review crops composite both variants on
white, gray, black, and magenta. The three known defect locations are
`cutout_01`, `cutout_02`, and `fringe_00`; `outer_soft` probes a delicate outer
edge.

```loop
name: vitmatte-scout-fixed-pipeline
topology: closed · inner · single
generator: scout_vitmatte_writer
verifier: root_separate_verifier
gate: .venv-gen/bin/python tasks/double-marine-bed-wrapper-batch/scouts/vitmatte/verify_scout.py
stop: done after exactly one ViTMatte architecture attempt produces dimension-valid same-alpha RGBA files and review boards, or blocked after a recorded MPS and CPU architectural failure
budget: max_iterations=1
```

The separate verifier owns acceptance. Visual boards are evidence for that
verifier, not a self-issued quality pass.

## Run

```bash
.venv-gen/bin/python tasks/double-marine-bed-wrapper-batch/scouts/vitmatte/run_vitmatte_scout.py
```

Outputs are written only to:

`.../images/Images/candidates/image14-research/vitmatte-scout/`

## Recorded result (2026-07-09)

- Native MPS forward succeeded on the first and only architecture attempt.
- Processor tensor: `1x4x1696x960`, representing bottom/right padding of 24/19
  pixels and no resize.
- Timings: model load 0.288 s, preprocess 0.074 s, forward 0.769 s,
  foreground recovery 0.102 s, total 2.974 s.
- Sampled MPS peaks: 1,351,413,248 bytes current allocation and
  4,107,026,432 bytes driver allocation. Process peak RSS was 1,185,366,016
  bytes.
- Raw model alpha remained soft (`99.10%` strictly between 0 and 1) and the two
  saved RGBA alpha channels are byte-identical.

Visual verdict: **feasible matting primitive, not a complete remover**. The full
board preserves delicate structures, but `cutout_02` still contains pale ghost
patches in an enclosed background area, `fringe_00` retains a light boundary,
and the outer fish edge still shows a halo on non-white backgrounds. Foreground
RGB recovery changes edge colors but cannot correct an alpha/topology error.
This is expected when an erroneous candidate region survives as sure foreground
in the trimap. A semantic/supervised trimap producer is therefore still needed.

Raw measurements and exact lineage are in the product-output `metrics.json`.
