# Chroma-regeneration scout evaluation

STATUS: COMPLETE — ALL CANDIDATES REJECTED

This was a bounded experiment, not a production promotion. Exactly four new
source-referenced model outputs were generated, one prior magenta regeneration
was copied as a read-only baseline, and no result was written to `Images/finals/`.
The source remained the native 941 x 1672 RGB PNG with SHA-256
`925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d`.

## Fixed method

- Target key for every new call: `#00FF00`. On the source non-paper proxy it had
  minimum CIEDE2000 23.1563, q0.1% 24.5752, and zero collisions below 15. Cyan
  was the next-best tested key (minimum 16.6431); red was unsafe (minimum
  7.9923). The key choice was made before generation.
- Prompt A SHA-256:
  `c87bcfa1cd6c85502ce5f7dd7e8aad63de6ca8e93a70bc54c7332a9486b88ca0`.
  Prompt B SHA-256:
  `5983f9a87d4bc16a7e0d285ce47a2cb22f864cadf1922db47c999c9ffd303f97`.
  Both reference the same source and the fixed style contract SHA-256
  `02e9830b3e04202b09b9f73949c3b6838384aaaf348d83e49ea58e2911dea31e`.
- Direct keying was RGB distance only: transparent radius 30, opaque radius
  115, smoothstep transition, no luma key. Despill only suppressed the dominant
  key channel in transition pixels, capped at 64 channel levels.
- Generation locks exist for the matrix and the single permitted transient
  Kontext retry. They were honored; no model call was rerun during finalization.

## Model-call ledger and disposition

| ID | Provider / model | Prompt | Seed | Call outcome | Visual / structural disposition |
|---|---|---:|---:|---|---|
| `flux2-a` | fal `fal-ai/flux-2-pro/edit` | A | 1403 | Valid first output, 20.3131 s, 576 x 1024 | Geometry close: ECC 0.9472, SSIM 0.8438, edge F1 0.9669, proxy alpha IoU 0.9093. Direct keyed RGB has conspicuous green rims on non-white backgrounds. |
| `nano-a` | Antigravity subscription `generate_image` | A | not exposed | Valid attempt 1, 68.3519 s, 768 x 1376 | Geometry close but scaled: ECC 0.9455, SSIM 0.7826, edge F1 0.9647, IoU 0.8887. Direct keyed RGB has conspicuous green rims. |
| `openai-a` | Codex subscription image tool via `gpt-5.4` | A | not exposed | Valid attempt 1, 99.0442 s, 1024 x 1536 | Rejected for major reframe/recomposition and changed object inventory. Aspect error 18.46%, ECC 0.3571, SSIM 0.3579, edge F1 0.6647. A keyable plate is not composition fidelity. |
| `kontext-b` | fal `fal-ai/flux-pro/kontext/max` | B | 1404 | First request ended in `RemoteDisconnected` before any HTTP response/image after 76.1589 s; charge unknown. One same-input transient retry succeeded in 33.5100 s, 752 x 1392. | Successful output ignored the requested green background: zero green key pixels, alpha fully opaque, and visible content fading/change. This is a visual/model-compliance failure, distinct from the transient transport failure. |
| `prior-magenta` | existing Cursor/OpenAI regeneration | prior | not exposed | Prior sunk call; no request made here; 941 x 1671 | Rejected. Magenta/purple collision proxy 4.13%, plus composition drift and colored fringe. |

Metered rate records are preserved in `manifest.json`: Flux 2 Pro edit was
documented at USD 0.03 for the first output MP plus USD 0.015 for extra
input/output MP; Kontext Max at USD 0.08 per image. Subscription calls have no
metered API charge recorded.

## Source-payload hybrid cold check

Only the two geometry-close green plates (`flux2-a`, `nano-a`) were eligible.
Their generated RGB was discarded. Their key-derived alpha was affine-registered
to the 941 x 1672 source, then the original source supplied the RGB payload and
`pymatting.estimate_foreground_ml` attempted white-paper foreground recovery.
Fully opaque payload pixels retain the source RGB byte-exactly. This isolated a
real insight: a generated chroma plate can supply useful enclosed-region
topology without imposing its regenerated palette, object changes, or green RGB
spill.

It did not produce a complete matte. The frozen, candidate-independent image14
benchmark was run unchanged:

| Candidate | Reconstruction MAE / p99 | Passed evidence | Frozen failures |
|---|---:|---|---|
| Flux source-aligned direct key, SHA `7961dc...3829` | 11.2160 / 118 | all sparse FG/BG guards; all 3 edge probes | `rgb_reconstruction`; vision independently rejects the bright green rim, which is far from paper-white and therefore does not trigger the white-edge metric |
| Flux source-payload hybrid, SHA `15029c...b3fd` | 2.3658 / 35 | all 3 labelled edge probes; all but one FG guard; all but one BG guard | `rgb_reconstruction`; pale-brown branch median alpha 93 < 96; cut00 enclosed gap p90 alpha 44 > 16 |
| Nano source-aligned direct key, SHA `a8216e...2e4a` | 12.4882 / 139 | all sparse FG/BG guards; all 3 edge probes | `rgb_reconstruction`; vision independently rejects the bright green rim |
| Nano source-payload hybrid, SHA `34a136...67b` | 1.7347 / 21 | all FG guards; all but one BG guard; fish-fin edge | `rgb_reconstruction`; cut00 enclosed gap; pink and right-seaweed white-edge probes |
| Assisted r110 control, SHA `ff34c2...ac17` | 0.8680 / 6 | reconstruction and every frozen FG/BG guard | pink-edge white fraction 0.3109 > 0.25; right-seaweed 0.2580 > 0.25 |

The comparison boards confirm the machine result. Direct regenerated RGB has a
bright green outline on gray, black, and magenta. The hybrids restore the
original composition and color but retain pale/paper edge contamination and
registration-dependent mistakes in enclosed gaps. Assisted r110 reconstructs
the source-over-white most accurately and clears every sparse semantic guard,
but still fails two white-edge probes; the native gray/black/magenta sand board
also exposes heavy background bleed through the pale base, confirming why a
machine guard pass is not visual approval. None clears the stated three-defect
contract; none is a final.

## Evidence

- Complete lineage, redacted call outcomes, costs, locks, prompts, and artifact
  hashes: product `manifest.json`, `matrix-attempt-lock.json`, and
  `kontext-transient-retry-lock.json`.
- Direct methods: product `comparison-board.png` and each candidate's
  `full-board.jpg`, six `crop-*.png`, `metrics.json`, keyed RGBA, and four
  composites. Flux/Nano also contain `source-aligned-direct-key/` with the
  941 x 1672 analysis RGBA, four composites, metrics, frozen report, and frozen
  review folder.
- Source-payload methods: `flux2-a/source-payload-hybrid/` and
  `nano-a/source-payload-hybrid/`, including 16-bit alpha, 941 x 1672 RGBA,
  four full composites, six crop boards, metrics, frozen report, and frozen
  review folder.
- Cross-method cold review: `final-method-comparison-full.png`, six
  `final-method-comparison-crop-*.png`, all six exact
  `final-benchmark-zone-*.png` review boards, and
  `final-method-comparison.json`.
- Assisted control frozen report/reviews:
  `assisted-r110-frozen-benchmark-report.json` and
  `assisted-r110-frozen-benchmark-review/`.

## Fresh verification record

The benchmark's negative-control suite passed with:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tasks/double-marine-bed-wrapper-batch/bg-benchmark/test_verify_bg_solution.py
.................... [100%]
20 passed in 0.24s
```

The unchanged verifier returned exit 1 for Flux direct, Nano direct, Flux
hybrid, Nano hybrid, and assisted r110 with the failure codes recorded above.
Structural lane verification and its negative self-test are the final closeout
gate; their fresh output is reported at handoff.

READY FOR JUDGING
