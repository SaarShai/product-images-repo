# Image 14 chroma-regeneration scout

## Scope and confidence

Done means four independently generated, source-referenced candidates and one
read-only prior baseline have complete lineage, deterministic chroma-key
artifacts, composition/key metrics, and native/crop review boards for a separate
parent verdict. A mechanically keyable but recomposed candidate fails.

Known:

- Source: original 941x1672 RGB image 14, SHA-256
  `925c34a39a0e2b5a09ad92ba39dace87f652bcc90ff8e063e2a6f644e735df9d`.
- Nano subscription and fal authentication passed live health checks.
- OpenAI subscription works with `gpt-5.4` plus `xhigh`; the user's default
  `gpt-5.6-sol` requires a newer CLI and the user's `ultra` effort is invalid for
  `gpt-5.4`. A scoped PATH wrapper adds only that effort override while the
  required `scripts/subgen.py --provider openai` remains the caller.
- The official Flux.2 Pro schema accepts reference `image_urls`, seed, PNG, and
  automatic/custom output size. Its fal page prices the first output megapixel
  at USD 0.03 and each extra input/output megapixel at USD 0.015.
- The official Kontext Max schema is a direct single-image editor accepting
  `image_url`, prompt, seed, PNG, and aspect ratio; the live fal page prices it
  at USD 0.08/image.

Assumed until outputs return: each provider will honor exact `#00FF00` and
preserve enough composition to permit fair registered analysis. Output-native
dimensions and any crop/recomposition remain visible.

Primary live schema sources:

- https://fal.ai/models/fal-ai/flux-2-pro/edit/api
- https://fal.ai/models/fal-ai/flux-2-pro/edit
- https://fal.ai/models/fal-ai/flux-pro/kontext/max/api
- https://fal.ai/models/fal-ai/flux-pro/kontext/max
- https://fal.ai/models/fal-ai/nano-banana-pro/edit/api

## Fixed matrix

| id | engine | family | source attachment | seed | cost class |
|---|---|---|---|---:|---|
| `openai-a` | subscription OpenAI via `subgen.py`, model `gpt-5.4` | A | `-i SOURCE` | unavailable | subscription |
| `nano-a` | subscription Nano Banana via `subgen.py` | A | `-i SOURCE` | unavailable | subscription |
| `flux2-a` | fal `fal-ai/flux-2-pro/edit` via `falgen.py` | A | `--image SOURCE` | 1403 | metered; approximately USD 0.03-0.045 |
| `kontext-b` | fal `fal-ai/flux-pro/kontext/max` via `falgen.py` | B | `--image SOURCE` | 1404 | metered; USD 0.08 |
| `prior-magenta` | existing Cursor regeneration, read-only baseline | prior | existing | unknown | sunk |

Kontext Max is used instead of fal Nano Banana Pro because the current wrapper
hard-codes 2:3 and warns that tall panels recompose; source aspect is 0.5628.

## Frozen keying and analysis

- One target for every new candidate: pure green `#00FF00` (RGB 0,255,0).
- Source-color selection oracle: pixels with CIELAB chroma >=7 or L* <=92.
  Candidate key colors are ranked by minimum, 0.01%, 0.1%, and 1% CIEDE2000
  distances plus collision rates. This is a selection proxy, not a subject mask.
- Key alpha uses RGB distance to target only: alpha 0 at radius <=30, alpha 1
  at radius >=115, smoothstep between. It is not luma-based.
- Despill changes only transition pixels and is capped at 64 green-channel
  levels. Raw candidate and no-despill RGBA remain available.
- Every raw output retains its native dimensions. Resizing and ECC registration
  are analysis-only and written under each candidate's analysis artifacts.
- Composition evidence: native aspect error, ECC registration correlation,
  registered SSIM, tolerant Canny-edge F1, and proxy silhouette IoU. Metrics are
  diagnostics; parent vision decides object/style preservation.

```loop
name: image14-chroma-regeneration-fixed-fleet
topology: closed · inner · fleet
generator: four independent engine calls, OpenAI subscription, Nano subscription, fal Flux.2 Pro edit, and fal Kontext Max
verifier: separate parent cold judge given only task, prompts, raw outputs, metrics, and review boards
gate: python3 ./tasks/double-marine-bed-wrapper-batch/scouts/chroma-regeneration/verify_scout.py PRODUCT_OUTPUT_DIR && parent vision confirms composition, objects, watercolor style, flat key plate, no collision, no spill, and no halo
stop: done when all four routes have one terminal valid-output attempt and the prior baseline is processed, or blocked with an exact auth/config/provider failure record
budget: max_iterations=1, max_candidates=4
quorum: all deterministic artifact checks pass and the separate parent accepts a candidate visually; mechanically keyable but recomposed is FAIL
anchor_files: tasks/double-marine-bed-wrapper-batch/scouts/chroma-regeneration/PLAN.md, PROMPT-A.md, PROMPT-B.md, STYLE-CONTRACT.md
state_store: product output manifest.json and task EVALUATION.md
recall: read state_store plus fixed prompts before every terminal call
writeback: record terminal status, provider, endpoint, prompt hash, reference hash, seed, native dimensions, output hash, duration, and cost class after every call
state_concurrency: single_writer
redaction: never persist FAL_KEY, authorization headers, data URIs, provider output URLs, or subscription auth; logs retain only local paths and redacted diagnostics
consent: user explicitly requested and authorized these four bounded source-referenced image calls in this task
verifier_blind: true
verifier_inputs: task, fixed prompts, raw outputs, deterministic metrics, review boards
on_error: one transient no-image retry is allowed per subscription route; auth/config/policy errors interrupt that route; unexpected or fal errors halt and surface without retry
output_actions: image generation max 4 valid candidates plus at most one transient no-image retry per subscription route; writes only to the two scoped directories
```

## Done means

1. Exactly four new terminal candidate records plus the prior baseline exist.
2. Every new route used the original source reference and one of only two frozen
   prompt families containing the logged style and anti-style contract.
3. Every valid raw output has native lineage, deterministic key/despill output,
   metric JSON, full board, and all named crop boards.
4. The verifier's negative fixture fails and the real structural gate passes.
5. The parent separately judges composition/style and declares any usable route;
   no scout self-promotes a candidate from metrics alone.
