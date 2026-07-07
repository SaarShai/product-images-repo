# PROBE S74 — can the codex CLI path reach gpt-image-2 (or which image model(s) does it expose)?

Date: 2026-07-06. Environment: codex-cli 0.139.0 (npm), logged in via ChatGPT account
(no OpenAI API key used). Working dir: `/Users/za/Documents/product images repo`.
No fal, no OpenAI API key, no paid billing touched anywhere in this probe.

## Method

1. Inspected `codex --help` / `codex exec --help` for any image-model-selection flag.
2. Read `~/.codex/config.toml` for a configured image model.
3. Tried to force `gpt-image-2` via `codex exec -m gpt-image-2` (the flag Codex exposes for
   *model selection*) and captured the raw API error.
4. Asked the running Codex agent (default model `gpt-5.5`, ChatGPT-account auth) to introspect
   its own image-generation tool schema and name the underlying model, non-interactively.
5. Asked the same agent whether it can control output size/aspect ratio via that tool.
6. Cross-checked with real evidence already on disk: pixel dimensions of images previously
   produced through this exact free path (`scripts/subgen.py` → `codex exec -i ... -`), and a
   vendored OpenAI model-reference doc bundled inside the Codex CLI install itself.
7. Re-confirmed `scripts/subgen.py --health` still reports the `openai` (codex) provider healthy
   right now, i.e. the free path is live, not just historically observed.

No image was generated in this probe (step 3 deliberately failed before generating; steps 4–5
are text-only introspection; step 6 reused images that already existed on disk from prior work —
zero new generation cost was incurred).

## Transcript 1 — is there a `-m` (model) flag, and does `-m gpt-image-2` work?

```
$ codex exec --skip-git-repo-check -m gpt-image-2 - <<'EOF'
Reply with the single word OK and nothing else. Do not generate an image.
EOF

OpenAI Codex v0.139.0
--------
workdir: /Users/za/Documents/product images repo
model: gpt-image-2
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: high
reasoning summaries: none
session id: 019f3709-779d-7cf1-9035-3523078936d4
--------
user
Reply with the single word OK and nothing else. Do not generate an image.

ERROR: {"type":"error","status":400,"error":{"type":"invalid_request_error","message":"The
'gpt-image-2' model is not supported when using Codex with a ChatGPT account."}}
ERROR: {"type":"error","status":400,"error":{"type":"invalid_request_error","message":"The
'gpt-image-2' model is not supported when using Codex with a ChatGPT account."}}
```

Interpretation: `-m` selects the **agent/reasoning model** Codex runs as (the loop that decides
what to do and call tools), not an image-generation backend. The API itself rejects
`gpt-image-2` in that slot, and says so explicitly: not supported on a ChatGPT-account login.
This is direct, first-party evidence — not a guess.

## Transcript 2 — what image tool/model does the (default model) agent actually have?

```
$ codex exec --skip-git-repo-check - <<'EOF'
Do NOT generate any image. Just answer with text.
Introspect on your own tool access: what is the exact name of the image-generation tool
available to you in this session, and if you know it, what underlying image model does it
call (e.g. gpt-image-1, gpt-image-2, dall-e-3, something else)? Also state any size/resolution/
aspect-ratio constraints or parameters you can pass to that tool ... say "UNKNOWN" for anything
you cannot determine from your own tool schema/system prompt.
EOF

model: gpt-5.5   provider: openai   session id: 019f3709-b310-7651-b432-571fe5c96b1d
--------
codex
The exact image-generation tool available to me in this session is:

`image_gen.imagegen`

Underlying image model: `UNKNOWN`

Parameters exposed by the tool schema:
`prompt?: string | null`

Size/resolution/aspect-ratio controls: `UNKNOWN`
Quality levels: `UNKNOWN`
Background transparency: `UNKNOWN`
Number of images / `n`: `UNKNOWN`
Seed/control parameters: `UNKNOWN`
Explicit edit mask/input-image parameters: `UNKNOWN`

The system description says the tool can generate images from descriptions and edit attached
images, but the callable schema I can see only exposes a single optional `prompt` field.
```

Interpretation: the agent itself cannot name the backing image model — the tool
(`image_gen.imagegen`) is opaque to it, exposing only a bare `prompt` string. This is honest
self-report, not evasion: the schema genuinely has no model/size fields for the agent to read.

## Transcript 3 — can size/aspect ratio be controlled through that tool?

```
$ codex exec --skip-git-repo-check - <<'EOF'
Do NOT generate any image. Just answer with text only.
If a user asks you to generate an image at a specific size ... can you actually control the
output pixel dimensions or aspect ratio via your image tool, or does the tool always decide
the size itself? ... say UNKNOWN if you are not sure.
EOF

codex
UNKNOWN for exact output pixel dimensions.

From my available image tool schema, I only have a `prompt` field and no explicit `size`,
`width`, `height`, or `aspect_ratio` parameter. So I cannot guarantee a requested size like
`1024x1024` or `1536x1024` through the tool interface. I can describe the desired aspect ratio
in the prompt, but the tool appears to decide the actual output dimensions itself.
```

## Cross-check A — real output dimensions from this exact free path, already on disk

`scripts/subgen.py`'s `gen_openai()` drives exactly `codex exec --skip-git-repo-check -i <imgs> -`
(the same free ChatGPT-account path probed above). Sampling PNGs already produced by prior
Brainer work under `~/.codex/generated_images/*/ig_*.png` (no new spend, pre-existing files):

```
ig_0b7dbe7c...png   (885, 1777)   RGB   ratio h/w ≈ 2.01
ig_0bd84f6e...png   (1166, 1349)  RGB   ratio h/w ≈ 1.16
ig_076e7058...(a)   (1165, 1350)  RGB   ratio h/w ≈ 1.16
ig_076e7058...(b)   (1166, 1349)  RGB   ratio h/w ≈ 1.16
ig_0eb0581a...png   (724, 2172)   RGB   ratio h/w ≈ 3.00
ig_008d7de8...png   (725, 2170)   RGB   ratio h/w ≈ 2.99
ig_0503175f...png   (963, 1633)   RGB   ratio h/w ≈ 1.70
ig_083da653...png   (725, 2170)   RGB   ratio h/w ≈ 2.99
```

Interpretation: even though the tool schema exposes no `size`/`aspect_ratio` field (transcripts
2–3), actual output aspect ratios vary widely and consistently match whatever aspect the calling
prompt asked for (tall door panels ≈2–3:1, near-square/portrait ≈1.16–1.7:1). So aspect-ratio
control **does work in practice**, but only indirectly — through prose in the prompt — never
through a structured parameter. This matches the wiki-memory entry `Geoguide input locks aspect`:
feeding a grey-body geometry-guide image as the FIRST attached image is what actually pins the
output aspect for this tool, not a size string. No output above is a bare 1024x1024 square,
which is the one shape this path reliably avoids when a non-square guide/prompt is given.

## Cross-check B — vendored OpenAI model-reference bundled inside the Codex CLI install

`~/.codex/vendor_imports/skills/skills/.curated/openai-docs/references/latest-model.md` (a
curated static reference file shipped with this Codex install, not a live API response) lists:

```
| gpt-image-2      | Best image generation and edit quality        |
| gpt-image-1.5     | Less expensive image generation and edit quality |
| gpt-image-1-mini  | Cost-optimized image generation                |
```

This confirms `gpt-image-2` exists as a named OpenAI model in their current lineup (per this
cached doc), but the file itself carries this caveat verbatim: "This file will drift unless
periodically re-verified against current OpenAI docs. If this file conflicts with current docs,
the docs win." It is NOT proof of which model the `image_gen.imagegen` tool actually calls
server-side for a ChatGPT-subscription Codex session — that mapping is not exposed anywhere we
can reach for free (transcripts 1–2 show it's both unnamed to the agent and explicitly rejected
if we try to force it via `-m`).

## Cross-check C — free path is live right now (not just historically)

```
$ python3 scripts/subgen.py --health
{'openai': 'ok', 'nano': 'ok'}
```

Both the `openai` (codex) and `nano` (agy/Nano Banana) free subscription providers responded
healthy at probe time.

## Findings

1. **Which image model(s) can codex invoke for free right now:** codex exposes exactly one
   image-generation surface to the agent: an opaque tool called `image_gen.imagegen`, callable
   only with a `prompt` string. The agent (running as `gpt-5.5`, the text/reasoning model) cannot
   name, select, or confirm the backing image model from its own tool schema — it self-reports
   `UNKNOWN`. There is no user-facing flag (`-m`, `-c`, or otherwise) that selects a *different*
   image backend; `-m` only changes the reasoning/agent model, which is a different axis
   entirely.

2. **Is `gpt-image-2` specifically reachable, and size constraints:** Attempting to force
   `gpt-image-2` into the model slot returns a first-party API error: *"The 'gpt-image-2' model
   is not supported when using Codex with a ChatGPT account."* This tells us `gpt-image-2` (as a
   directly-selectable *chat/agent* model id) is API-gated away from ChatGPT-subscription Codex
   sessions — consistent with `gpt-image-2` being an image-specific model that isn't meant to sit
   in the agent-model slot at all. Whether the *internal* `image_gen.imagegen` tool routes to
   gpt-image-2, gpt-image-1.5, or something else under the hood is genuinely UNKNOWN from
   anything reachable without an API key — OpenAI does not expose that mapping to ChatGPT-account
   Codex sessions. Size: there is no explicit size/resolution/aspect-ratio parameter in the tool
   schema (self-reported "UNKNOWN" for size control), but empirically (Cross-check A) the actual
   output aspect ratio DOES follow the prompt/attached-guide-image aspect (observed outputs
   ranging ≈1.16:1 to ≈3.0:1 h/w, never forced to a fixed square) — so aspect is steerable
   indirectly via prose/reference image, never via a structured size string.

3. **Recommendation for route C (does paid-fal remain finals-only, or does free image-2 exist):**
   Keep paid-fal (or paid OpenAI-API gpt-image-2 direct) as the **finals-only / when-explicit-
   size-or-model-guarantee-is-required** path. The free codex path (`scripts/subgen.py --provider
   openai`) remains the correct **default/free/iteration path** exactly as documented in
   `scripts/subgen.py`'s own docstring and the `subscription-image-gen-one-path` wiki entry — it
   is live, healthy, and already produces non-square/geometry-following output — but it CANNOT
   currently guarantee "this exact call used gpt-image-2" nor guarantee an exact pixel size,
   because neither the model identity nor a size parameter is exposed through the ChatGPT-account
   Codex tool surface. If a downstream task needs a contractually-exact model id or exact pixel
   dimensions (not just an aspect the guide image nudges it toward), that requirement can only be
   met on the paid API path, not the free codex path.

## Honest gaps / UNKNOWNs

- We could not determine, from any free/no-API-key-visible surface, the literal model id that
  `image_gen.imagegen` calls server-side inside a ChatGPT-account Codex session. This would
  require either an OpenAI-side admission (not published anywhere we found) or a paid API-key
  call with response metadata that names the model — out of scope for this probe (no paid image
  generation permitted).
- We did not run an actual image generation in this probe (not required to answer the DONE MEANS
  questions, and avoids even the appearance of spend); Cross-check A instead reused
  already-existing prior-work outputs from this exact free path as real evidence of behavior.
- `codex features list` was not explored further for a hidden image-model toggle; the `--help`
  surface and `~/.codex/config.toml` showed no image-model-selection mechanism, so this was not
  pursued as a second attempt (diminishing likelihood, per the 2-attempt cap).
