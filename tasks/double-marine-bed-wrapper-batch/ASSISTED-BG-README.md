# Assisted background-removal core

`assisted_bg_remove.py` is the candidate-generation core for the correction-led
route. It does not decide whether an image is correct and it cannot promote an
output to `Images/finals/`.

## Contract

- Source: native-size, 8-bit `RGB`. The source is never resized or overwritten.
- Proposal: the exact same dimensions, as `L`, grayscale `RGB`, or `RGBA`
  (alpha is used). No implicit resize is allowed.
- Corrections: optional exact-size, genuinely transparent `RGBA`:
  - alpha `0` = unknown / no instruction;
  - opaque pure red = sure foreground;
  - opaque pure blue = sure background.
- Anti-aliased/partly transparent, weak-colored, magenta/ambiguous, fully
  opaque, flattened, or size-mismatched correction files are rejected. Use a
  hard round pencil/brush and preserve transparency when exporting the marks.
- Proposal morphology runs first. A configurable radius around correction
  strokes is then returned to unknown, the exact red/blue pixels are applied,
  and those pixels are clamped again after the solver. Pale or white pixels
  marked foreground are never removed by a luma rule.
- `--backend` is mandatory. `vitmatte` uses the locally cached official
  `hustvl/vitmatte-small-composition-1k` revision and chooses MPS when available.
  `closed_form` uses PyMatting. ViTMatte never silently falls back; fallback is
  possible only with `--allow-fallback` and is recorded in metrics.
- Output is soft, straight/unassociated RGBA by default. `--binary` is an
  explicit separate mode. Foreground RGB comes from `estimate_foreground_ml`,
  followed by a bounded residual correction only at safe alpha values. A final
  joint edge-decontamination stage borrows colorful high-alpha RGB only from
  the same connected component and solves a replacement alpha that preserves
  the source-on-paper appearance within 8/255 per channel. It protects every
  sure-FG/sure-BG label and never lowers a changed pixel below the foreground
  support threshold. The core contains no white/luma punch or edge deletion.
  Joint decontamination is intentionally skipped for explicit binary output.
- Candidate RGBA, metrics, manifest, and four-background review-board paths
  must all be supplied. Any path under a `final/` or `finals/` component is
  refused. The manifest stays `candidate-unapproved` until independent
  benchmark, native-resolution visual, and user review gates pass.

## Example

```bash
.venv-gen/bin/python \
  tasks/double-marine-bed-wrapper-batch/assisted_bg_remove.py \
  --source /absolute/path/source-rgb.png \
  --proposal /absolute/path/proposal-alpha-native.png \
  --corrections /absolute/path/corrections-transparent-rgba.png \
  --backend vitmatte \
  --output /absolute/path/Images/candidates/assisted/image14-rgba.png \
  --metrics /absolute/path/Images/candidates/assisted/image14-metrics.json \
  --manifest /absolute/path/Images/candidates/assisted/image14-manifest.json \
  --review-board /absolute/path/Images/candidates/assisted/image14-review.png
```

Use `--device mps` to require Apple GPU execution or `--device cpu` to require
CPU. With the default `--device auto`, ViTMatte chooses MPS when it is available
and otherwise uses CPU; that device choice is recorded.

Useful controls:

- `--inner-distance` / `--outer-distance`: shrink proposal sure-FG/sure-BG and
  leave a wider solver band.
- `--correction-unlock-radius`: make an unknown neighborhood around sparse
  strokes while keeping each stroke pixel exact.
- `--residual-alpha-floor`: never divide by alpha below this value.
- `--residual-max-adjustment`: per-channel bound for source-on-paper residual
  correction.
- `--no-edge-decontamination`: diagnostic opt-out from the default joint
  straight-RGB/alpha edge cleanup. Normal soft-alpha production should leave it
  enabled.
- `--binary`: deliberately produce binary alpha; this is off by default.

## Tests

```bash
python3 -m pytest -q \
  tasks/double-marine-bed-wrapper-batch/tests/test_assisted_bg_remove.py
```

The default suite injects small stub solvers and does not load a model. An
optional real-backend smoke test is present but skipped unless explicitly
armed:

```bash
ASSISTED_BG_REAL_BACKEND=closed_form python3 -m pytest -q \
  tasks/double-marine-bed-wrapper-batch/tests/test_assisted_bg_remove.py \
  -k real_backend
```

Use `vitmatte` instead of `closed_form` to exercise the cached model. A smoke
pass proves only that the backend executes and returns bounded native-size
alpha; it is not visual or semantic acceptance.
