# Double Marine background-removal benchmark

This package is an independent rejection gate. It does **not** remove a
background and does not infer truth from the candidate being graded.
The check-by-check acceptance contract is in `RUBRIC.md`.

## What is frozen

- Original and x4 pre-removal RGB identities (dimensions plus SHA-256).
- Sparse sure-foreground and sure-background guards selected visually from the
  original image. The prior user defect crops were used only to locate regions;
  no candidate color or alpha threshold produced the labels.
- Three or more source-selected edge probes per case, including the
  user-reported image14 fringe locations.
- Conservative machine thresholds plus mandatory native multi-background human
  review for continuous watercolor fades.

`image14`, `image15`, and `sample08` are ready, with frozen original and x4
identities plus independent source-only annotations. For image15, visible sand
and watercolor wash at the base is foreground, and uniform cream paper beyond
its visible fade is background. The exact terminal fade remains a mandatory
human-review region rather than a machine-labelled boundary.

A source-only annotation-quality audit also checks the semantic premise of each
edge probe: at least 75% of the intended boundary must genuinely be
pigment-colored at RGB distance 80 or more from paper. Intentional white or
cream subject highlights remain foreground, not contamination. This audit
replaced image15's initial bubble probe with a pigment-lined salmon-coral outer
contour; no candidate result or threshold change informed that correction.

## Paper-color source contract

Paper color is also frozen from source-only evidence. Each row combines the 81
pixels in each of six exterior-background disks (`n=486`); spread is the
per-channel 5th–95th percentile interval.

| Case | Robust median RGB | 5th–95th percentile RGB | MAD | Contract |
|---|---:|---:|---:|---|
| image14 | `[254, 254, 254]` | `[253,253,253]–[255,255,255]` | `[0,0,0]` | global white |
| image15 | `[250, 246, 241]` | `[249,245,240]–[251,247,243]` | `[0,0,1]` | case-level cream |
| sample08 | `[254, 254, 254]` | `[253,253,253]–[255,255,255]` | `[0,0,0]` | global white |

Image15's median is Euclidean RGB distance `17.38` from white, while the other
two medians are only `1.73` away. The manifest and annotation therefore freeze
`image15.paper_rgb = [250, 246, 241]`. The verifier prefers a case-level value
over the annotation copy and global default, rejecting disagreement rather than
silently choosing one.

## Machine gate

The verifier checks:

1. Source/reference hashes and exact candidate dimensions at a benchmarked
   integer scale (x1 or x4 for all three ready cases).
2. RGBA presence, non-degenerate alpha, and straight-RGB reconstruction when
   recomposited over the original paper color.
3. Every sure-FG disk, exterior BG disk, and enclosed/interior BG disk.
4. White/paper-colored pixels in manually located foreground boundary bands.
5. Deterministic composites on white, gray, black, and magenta.

Run it with a candidate override:

```sh
python3 tasks/double-marine-bed-wrapper-batch/bg-benchmark/verify_bg_solution.py \
  --manifest tasks/double-marine-bed-wrapper-batch/bg-benchmark/manifest.json \
  --candidate image14=/absolute/path/to/candidate.png \
  --json-report /tmp/image14-bg-verdict.json \
  --review-dir /tmp/image14-bg-review
```

Exit 0 means **machine checks passed**, not production approval. The JSON and
console output still say `PENDING_HUMAN_REVIEW` until a person inspects all
listed native crops on the four backgrounds.

## Negative controls

`build_negative_fixtures.py` creates a known-good synthetic watercolor-like
shape and explicit corruptions for white fringe, deleted foreground, retained
enclosed background, bad dimensions, wrong format, missing alpha, degenerate alpha, and
premultiplied/incorrect RGB. Tests require each corruption to trip its named
failure code. This prevents a gate that has only ever passed.

```sh
python3 tasks/double-marine-bed-wrapper-batch/bg-benchmark/build_negative_fixtures.py \
  --output-dir /tmp/bg-negative-fixtures
pytest -q tasks/double-marine-bed-wrapper-batch/bg-benchmark/test_verify_bg_solution.py
```

## Rubric boundary

The machine gate catches known, labelled failures. It does not claim that sparse
guards prove every unlabeled pixel or that an aesthetic watercolor transition is
objectively decidable. Any ambiguity is surfaced in `human_review`; weakening a
threshold or moving a guard after seeing a candidate invalidates the benchmark
version and requires a documented new version.
