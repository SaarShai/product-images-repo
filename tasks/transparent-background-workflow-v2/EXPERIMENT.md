# Clear-edge solid-background prompt experiment

## Frozen goal

Optimize prompt structure and exact snippets for reference-style illustrations with clean, clearly contrasted edges against a solid background. Background removal, alpha, keying, matting, upscaling, and final promotion are out of scope.

## Round 1 — evidence shown to user

Shared: same reference input, content block, watercolor style block, white-background block, provider route.

- A: control prompt. Raw output `arm-a-white-control.png`.
- B: A plus closed contours, colored outlines / line art matching / color hold, and interior-white separation. Raw output `arm-b-colored-outlines.png`.

Observed:

- Aura index: A `0.1316`; B `0.0800` (lower is cleaner).
- Blind vision: edge clarity A `3.6/5`, B `4.8/5`; contour continuity A `3.4/5`, B `4.7/5`; watercolor/style match A `4.6/5`, B `4.0/5`.
- B visibly improves edge separation but becomes brighter, flatter, and more strongly inked.
- Attribution limit: B changes closed boundaries, outline treatment, and interior whites together. One sample per arm also confounds prompt effect with generation noise.
- C native-alpha request is excluded from prompt-payoff evidence because it returned an opaque painted checkerboard and changed output mode.

## Round 2 — frozen, not generated pending feedback

1. A2: repeat A unchanged to estimate generation noise.
2. D: A plus palette lock, crisp closed boundary, and interior-light separation; explicitly forbids added/stronger outlines.
3. E: D plus one thin, subtle, fully continuous locally color-matched outer boundary line.

Primary comparison: D vs E isolates incremental outline payoff. A/A2 bounds seed noise. User feedback selected the hybrid target: A's muted watercolor palette plus B's definition, with lower saturation, no broken outline segments, and no background-white-looking subject areas.

## User feedback after Round 1

- B: better definition and contrast against the background; too saturated; outline gaps remain.
- A: better style and color palette; many outline gaps and many white-looking areas inside the illustration.

## Later ablations

- Interior-light separation: selected Round-2 prompt with vs without tinted off-white interior-light clause.
- Anti-aura: identical prompt with vs without only the anti-aura clause; compare raw solid-background boundary, not extracted alpha.
- Repeat the winning structure on a second reference before banking it as reusable guidance.

## Round 2 — generated after user feedback

- A2: unchanged A repeat; estimates unseeded generation variance.
- D: palette lock + crisp closed boundary + tinted interior lights; no added outline.
- E: D + thin, fully continuous, locally color-matched outer outline.

Raw metrics:

| Arm | Aura index | Boundary saturation | Boundary/background RGB distance |
|---|---:|---:|---:|
| A | 0.1316 | 12.90% | 75.88 |
| A2 | 0.1049 | 15.13% | 87.02 |
| D | 0.1216 | 12.67% | 75.28 |
| E | 0.0839 | 13.32% | 83.69 |

Blind vision verdict: E is the best A-palette/B-definition compromise. D preserves watercolor best but still fades at pale green/peach branches. E has fewer outline breaks and stronger background contrast without B's saturation, but minor breaks remain at pale-green upper-left tips, fine pink left-side sprigs, and isolated top-pink highlight edges. One sample per treatment is directional evidence, not a bankable causal result.
