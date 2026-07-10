---
name: transparent-product-image-gen
description: Use when a product needs a NEW transparent-background (RGBA) illustration generated from scratch, or an EXISTING finished illustration needs its white/paper background removed, for Screenery/Wanderland product images. Also use when a downstream tool cannot accept an alpha channel and needs a flat keyable background color instead. Do NOT use for style edits of existing art via images/edits (composition drifts — see Rejected routes), and do NOT reach for luma/flood "punch" background removal on watercolor art (deletes real pale paint).
status: proposed
disable-model-invocation: true
auto-install: false
pulse_reminder: proposed + slash-only — this skill will NOT auto-fire until promoted via skills/learn-skill/tools/learn.py promote. Always run the edge-hygiene prompt block verbatim on route A/C; never skip the user-review STOP on route E.
---

# transparent-product-image-gen

> **Proposed skill.** Born untrusted (slash-only, `disable-model-invocation: true`,
> `auto-install: false`) per Brainer's `learn-skill` convention — it will not
> auto-fire on context match. Invoke it explicitly (`/transparent-product-image-gen`
> or by name) until usage telemetry clears it for promotion:
> `python3 skills/learn-skill/tools/learn.py promote --name transparent-product-image-gen`.
> Written for a weaker/cheaper executor: every command below is copy-pasteable
> with real repo paths. Do not improvise alternate flags or invent commands not
> shown here.

This is the session-proven, evidence-backed procedure for getting a transparent
(RGBA) product illustration. It replaces ad-hoc re-derivation: read the
DECISION TREE first, then run the exact commands for your route. All evidence
below was measured on the `double Marine Bed Wrapper` task
(`tasks/double-marine-bed-wrapper-batch/`); primary sources are cited inline so
you can re-verify instead of trusting this doc blindly.

## When to Use
- A product needs a **new** transparent-background (RGBA) illustration
  generated from scratch (no existing finished art to preserve).
- An **existing** finished illustration needs its white/paper background
  removed without redrawing/regenerating it.
- A downstream tool cannot read a PNG alpha channel and needs a flat,
  keyable background color instead.
- NOT for: editing one element of already-finished art (→ `element-edit`);
  fitting art to an exact SVG die-cut contour (→ `svg-template-illustration`);
  "cleaning up" an existing image via `images/edits` or any regeneration
  (rejected route — see table below; matte it instead, Route E).

## Procedure — decision tree

```
Do you have a NEW image to create (no existing finished art to preserve)?
├── YES → does the downstream consumer need a flat KEY COLOR instead of alpha
│         (e.g. a compositor that can't read PNG alpha)?
│         ├── NO  → ROUTE A (native transparent generation) + ROUTE B (upscale)
│         └── YES → ROUTE C (keyable magenta generation), same model
│
└── NO, I have an EXISTING finished illustration and need its background removed
          → ROUTE E (Adobe-assisted matting + frozen gate + MANDATORY user review)
          Do NOT use images/edits or a chroma regeneration to "remove" an existing
          image's background — both are REJECTED routes (see table below).
```

STOP-and-ask-user points (do not proceed past these without explicit approval):
1. **After the first ROUTE A/C generation** — show the raw RGBA (composited on
   white/gray/black/magenta) to the user before spending more generations or
   upscaling. Style/composition approval happens here, not after upscaling.
2. **Before promoting any ROUTE E candidate out of `Images/candidates/`** — a
   machine `machine_pass=true` is `PENDING_HUMAN_REVIEW`, never final. The user
   has previously rejected a machine-passing candidate on native 1:1 review
   (see Pitfalls). Native-resolution review on white/gray/black/magenta is
   mandatory every time, no exceptions.

---

## ROUTE A — Native transparent generation (WINNER, new images)

**Model:** OpenAI `gpt-image-1`, `POST https://api.openai.com/v1/images/generations`,
`background=transparent`, `quality=high`, `size` matched to the image's aspect
(portrait product art used `1024x1536`). Returns a **real RGBA** image (not a
fake checkerboard — see Rejected routes for the subscription-path failure).
Key: `.secrets/openai.env` (`OPENAI_API_KEY=...`), loaded the same way
`scripts/openai_edit.py` already does it (`scripts/_falcommon.py::load_openai_key()`).

### Mandatory edge-hygiene prompt block (verbatim — append to every generation prompt)

```
every object has clearly defined, fully closed outlines; no shape fades into
the background; edges crisp; interior highlights enclosed by visible outlines
```

Measured effect (image14 probe, `REVIEW/marine-bg-complete/image14-gen-api/INDEX.md`,
raw evidence in Drive `.../images/Images/candidates/bg-gen-api-v1/image14/`):
without this block, stray fully-enclosed background pockets trapped inside the
foreground alpha were **79–169** per image (noisy mask). With this block
appended, the same prompt+model dropped to **1** stray pocket, area 1px —
essentially a clean alpha boundary. Semi-alpha (soft/antialiased) pixels also
dropped to roughly 0.3% of the frame in the clean run. This is the single
biggest lever found this session — never omit it.

### Exact runnable command

There is no checked-in wrapper for `images/generations` yet (only
`scripts/openai_edit.py` wraps `images/edits`). Run this self-contained
snippet, adjusting `PROMPT` and `SIZE`:

```bash
cd "/Users/za/Documents/product images repo"
python3 - <<'PY'
import base64, json, sys
from pathlib import Path
sys.path.insert(0, "scripts")
import requests
from _falcommon import load_openai_key

PROMPT = (
    "watercolor illustration of <YOUR MOTIF HERE>, soft loose wet-on-wet "
    "watercolor washes, <YOUR PALETTE>, product-illustration style, isolated "
    "single subject, "
    "every object has clearly defined, fully closed outlines; no shape fades "
    "into the background; edges crisp; interior highlights enclosed by "
    "visible outlines"
)
SIZE = "1024x1536"   # match aspect: 1024x1024 square, 1536x1024 landscape, 1024x1536 portrait
OUT = Path("/absolute/path/to/Images/candidates/gen-api-v1/out1.png")

key = load_openai_key()
r = requests.post(
    "https://api.openai.com/v1/images/generations",
    headers={"Authorization": f"Bearer {key}"},
    json={
        "model": "gpt-image-1",
        "prompt": PROMPT,
        "n": 1,
        "size": SIZE,
        "quality": "high",
        "background": "transparent",
    },
    timeout=180,
)
r.raise_for_status()
j = r.json()
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_bytes(base64.b64decode(j["data"][0]["b64_json"]))
print("OK ->", OUT, "usage:", j.get("usage"))
PY
```

**Cost (measured, image14 arm P2b — the winning config: edge-hygiene + transparent,
quality=high, n=1, 58.3s):** `usage = {input_tokens: 62, output_tokens: 6240,
total: 6302}`. Without the hygiene block (arm P2, n=2 in one call, 57.1s):
`{input_tokens: 48, output_tokens: 12480, total: 12528}` for 2 images — i.e.
roughly the same per-image token cost either way; the hygiene block is free
quality, not an extra-cost option.

**STOP:** after this call, composite the RGBA on white/gray/black/magenta
(see Verification) and get user sign-off on style/composition before doing
anything else (upscaling, more generations).

---

## ROUTE B — Alpha-aware x8 upscale (after Route A/C sign-off)

RealESRGAN corrupts alpha if you feed it RGBA directly. Use the `split` method:
RGB channels go through RealESRGAN, the alpha channel is Lanczos-resized
independently, and they are recombined. Never use `--method two-plate` or
`--method direct` for production — `direct` records ncnn's undocumented native
RGBA behavior and `two-plate`'s nonlinear black/white-plate alpha recovery
leaks foreground texture into alpha (both noted as inferior to `split` in
`tasks/double-marine-bed-wrapper-batch/PLAN-bg-complete-solution.md`, "Alpha-safe upscale").

```bash
cd "/Users/za/Documents/product images repo"
python3 tasks/double-marine-bed-wrapper-batch/alpha_aware_upscale.py \
  /absolute/path/to/decontaminated-source-rgba.png \
  /absolute/path/to/Images/candidates/gen-api-v1/out1-x8.png \
  --method split \
  --scale 8 \
  --review-board /absolute/path/to/Images/candidates/gen-api-v1/out1-x8-review.png \
  --metrics /absolute/path/to/Images/candidates/gen-api-v1/out1-x8-metrics.json \
  --ack-decontaminated-straight-rgb
```

Notes:
- `--ack-decontaminated-straight-rgb` is a REQUIRED flag, not optional — it is
  a deliberate acknowledgment gate that the input's foreground RGB is already
  decontaminated (straight, unassociated alpha). The script refuses to run
  without it.
- The input must already have a real alpha channel with both fully-transparent
  and fully-opaque pixels, and at least one soft edge pixel — a hard binary
  mask will be rejected.
- Verified this session: alpha MAE 0 / max error 0 vs the prescribed Lanczos
  reference, source SHA-256 unchanged before/after (the script checks this
  itself and raises if the source file was touched).
- `--review-board` auto-generates the four-background (white/gray/black/magenta)
  composite for the next verification step — always pass it.

---

## ROUTE C — Keyable fallback (same model, when alpha is not usable downstream)

Same `gpt-image-1` `images/generations` call as Route A, but:
- `background: "opaque"` (not `"transparent"`)
- Append to the prompt (after the edge-hygiene block):
  `"background: perfectly uniform solid pure magenta #FF00FF, flat solid fill, no watercolor texture in background, zero gradient, no magenta anywhere on the subject"`
- **Pick the key color per image** — it must be absent from the art's own
  palette (magenta was safe for the coral/turtle/teal palette tested; a
  coral-pink product would need a different key color).

Measured result (`REVIEW/marine-bg-complete/gen-model-matrix/INDEX.md`, Arm 3):
the model never renders a colorimetrically pure `#FF00FF` (0% ΔE<5 to the
literal target), but measured against its *own* actual sampled fill color:
**68.8% of pixels ΔE<5, 0% edge-band spill, only 4 enclosed pockets** (best of
the 3 keyable arms tested — Recraft V4 and Flux/dev were both worse, see
Rejected routes). Treat this as "requires a real despill/key algorithm
afterward," not a one-shot perfect key.

**Cost:** usage `{input_tokens: 103, output_tokens: 6240, total: 6343}`
(48.5s, n=1).

---

## ROUTE E — Existing image, background removal (Adobe-assisted, user-gated)

For an **already-finished illustration** where you must remove its background
without regenerating/redrawing it. This is a 4-stage pipeline; do not skip a
stage or short-circuit the gate.

### Stage 1 — Semantic proposal (Adobe, interactive)
Use the Adobe MCP connector's remove-background action on the source image to
get a first-pass alpha/RGBA **proposal** (not a final answer — just a trimap
seed). This is an interactive MCP tool call, not a CLI script.

### Stage 2 — Correction-led matting
```bash
cd "/Users/za/Documents/product images repo"
.venv-gen/bin/python \
  tasks/double-marine-bed-wrapper-batch/assisted_bg_remove.py \
  --source /absolute/path/source-rgb.png \
  --proposal /absolute/path/adobe-proposal-alpha-native.png \
  --corrections /absolute/path/corrections-transparent-rgba.png \
  --backend vitmatte \
  --output /absolute/path/Images/candidates/assisted/imageNN-rgba.png \
  --metrics /absolute/path/Images/candidates/assisted/imageNN-metrics.json \
  --manifest /absolute/path/Images/candidates/assisted/imageNN-manifest.json \
  --review-board /absolute/path/Images/candidates/assisted/imageNN-review.png
```
- `--corrections` is optional (sparse red=sure-FG / blue=sure-BG strokes on a
  transparent RGBA layer, alpha=0 where you have no opinion). Only add them
  where the proposal is visibly wrong.
- `--correction-unlock-radius` (default 6) controls how far around each stroke
  the trimap is reopened to "unknown." **Unlock-radius trap:** a wide radius
  (e.g. 110px) can reopen and break a nearby, previously-correct region — this
  was observed directly (`REVIEW/marine-bg-complete/INDEX.md`, image15/sample08
  round-2 corrections). Prefer a narrow radius (R=24 was the value that worked
  without side effects in that case) and re-run the gate after every change.
- The script physically refuses to write into any path containing `final/` or
  `finals/` — it can only produce candidates.

### Stage 3 — Frozen machine gate (mandatory before any human review)
```bash
cd "/Users/za/Documents/product images repo"
python3 tasks/double-marine-bed-wrapper-batch/bg-benchmark/verify_bg_solution.py \
  --manifest tasks/double-marine-bed-wrapper-batch/bg-benchmark/manifest.json \
  --candidate imageNN=/absolute/path/to/Images/candidates/assisted/imageNN-rgba.png \
  --json-report /tmp/imageNN-bg-verdict.json \
  --review-dir /tmp/imageNN-bg-review
```
Exit 0 / `machine_pass=true` means the automated FG/BG guards, edge probes, and
straight-RGB reconstruction all passed — it does **not** mean the image is
approved. The gate itself prints `PENDING_HUMAN_REVIEW` even on a full pass.
If your image has no frozen guard annotations yet (i.e. it isn't one of
image14/image15/sample08), run the triage scanner first to find candidate
defect regions to look at:
```bash
python3 tasks/double-marine-bed-wrapper-batch/batch_triage.py \
  --source /absolute/path/source-rgb.png \
  --candidate /absolute/path/candidate-rgba.png \
  --report /tmp/imageNN-triage.json \
  --review-sheet /tmp/imageNN-triage-sheet.png
```
`batch_triage.py` never blocks (exit 0 unless I/O fails) — it is a review
prompt, not a gate.

### Stage 4 — STOP: mandatory user review
**A machine pass is never the finish line.** Show the user the native
resolution `--review-board` composite on white/gray/black/magenta (Stage 2's
output) and wait for explicit approval before this candidate can be copied
into `Images/finals/`. This is not a formality: the user has previously
**rejected a machine-passing candidate** after inspecting it at 1:1 (see
`REVIEW/marine-bg-complete/INDEX.md`, "sample08 ... coral-fork correction
widened a real gap ... may show as a slightly wider notch"). Do not promote
without that explicit sign-off.

---

## Verification (run these, don't eyeball)

1. **Alpha histogram check** (routes A/B/C — proves the alpha channel is real
   and non-degenerate, not a checkerboard or all-opaque fallback). The pattern
   already shipped in `alpha_aware_upscale.py::alpha_stats()`:
   ```python
   import numpy as np
   from PIL import Image
   a = np.asarray(Image.open("out1.png").convert("RGBA").getchannel("A"), dtype=np.uint8)
   print({
       "min": int(a.min()), "max": int(a.max()), "unique": int(np.unique(a).size),
       "zero_pct": float(100 * np.mean(a == 0)),
       "soft_pct": float(100 * np.mean((a > 0) & (a < 255))),
       "opaque_pct": float(100 * np.mean(a == 255)),
   })
   ```
   Reject if `min==max` (flat/degenerate alpha) or `unique==1`.

2. **Enclosed-pocket check** (routes A/C — catches the "79–169 stray pockets"
   failure mode the edge-hygiene block fixes; not a checked-in script, run
   inline):
   ```python
   import numpy as np
   from PIL import Image
   from scipy import ndimage as ndi
   a = np.asarray(Image.open("out1.png").convert("RGBA").getchannel("A"))
   bg = a == 0
   labeled, n = ndi.label(bg)
   border_labels = set(labeled[0, :]) | set(labeled[-1, :]) | set(labeled[:, 0]) | set(labeled[:, -1])
   enclosed = [i for i in range(1, n + 1) if i not in border_labels]
   print(f"{len(enclosed)} enclosed background pocket(s)")
   ```
   1–4 small pockets (few px, real topology like a gap between coral branches)
   is fine; dozens is the noisy-mask failure — regenerate with the hygiene
   block if you skipped it.

3. **1:1 edge crops on white/gray/black/magenta** (all routes — the ONLY way
   edge quality is judged, per repo-wide rule: geometry/edges are judged by a
   registered overlay/crop, never a "quick read" of the full image). Both
   `alpha_aware_upscale.py --review-board` and `assisted_bg_remove.py
   --review-board` already generate this four-background composite for you —
   open it and zoom to 400%+ at the object boundary. Never approve from the
   thumbnail-scale full image.

4. **Route E gate** — Stage 3's `verify_bg_solution.py` above; exit code
   0/1 is a real pass/fail signal, but `machine_pass=true` still requires
   Stage 4's human review (see STOP points).

---

## Rejected routes (do not re-probe these — evidence already collected)

| Route | Verdict | One-line reason (evidence) |
|---|---|---|
| **gpt-image-2** | Rejected for transparency, probed live (direct API) | Direct OpenAI API call (`images/generations`, `model=gpt-image-2`, `background=transparent`) returned HTTP 400: `"Transparent background is not supported for this model." (param: background, code: invalid_value)` — 2026-07-10. The fal wrapper independently exposes no `background` param. Fine model otherwise; just not a transparency source. |
| **Recraft V3** (fal) | Rejected, schema-only | No `background`/alpha field at all in its live schema (`prompt, colors, style_id, style, image_size` — no transparency lever whatsoever). Not probed live; ruled out by schema inspection alone. |
| **Recraft V4** (fal) | Rejected, probed live | `background_color` param is unreliable: requested magenta `#FF00FF`, actually rendered solid **crimson** (`RGB(255,2,48)`, 0.0% ΔE<5 to the request). Even against its own actual color, 1063 enclosed background pockets from coral-gap topology. |
| **Flux/dev keyable** (fal, prompt-hack) | Rejected, probed live | Total failure to follow the background-color instruction — sampled corner `RGB(253,238,235)` (pale blush), 0.0% match at any ΔE tolerance to magenta. |
| **LayerDiffuse** (local ComfyUI 0.25.0, SDXL attn-injection) | Rejected, probed live | Produces a REAL per-pixel alpha channel, but the mask does not track the subject: opacity concentrated in scattered blotches near canvas edges/corners while the actual illustrated subject rendered mostly transparent (training assumes single-object-floating-in-void prompts, not full-scene prompts). |
| **Subscription-path image gen** (ChatGPT UI / non-API "native transparency") | Rejected, probed live | Both allowed subscription calls returned **opaque RGB PNGs depicting a fake checkerboard pattern** (not a real alpha channel) and changed composition details — not a dependable transparency source. |
| **images/edits on existing art** (gpt-image-1, to reproduce/preserve an existing illustration on transparent bg) | Rejected, probed live | Hard server-side ~61.2s timeout (`RemoteDisconnected`, not a client timeout) at `quality=high` or `input_fidelity=high`, reproduced 100% of trials. Only `quality=medium` completes, and even then composition drifts — mean-abs-diff-RGB over the opaque region was **44.3–46.0/255** vs the source (a regeneration, not a pixel-preserving cutout), with inconsistent small-bubble survival (5–6 of 7 across 2 samples). |
| **Pure-luma flood/punch removal** (white-key style) | Rejected, real-world failure across multiple attempts | The "flood FG ∧ restore" family (and its `--pure-luma` threshold variants) repeatedly deleted real pale painted content — ultra-pale ghosts and residual fringe — while a proxy metric (`white_rim=0`) reported success; **the proxy metric directly contradicted user inspection** (`PLAN-bg-complete-solution.md`, "Known from prior work"). `assisted_bg_remove.py`'s production core deliberately contains **no** white/luma punch or edge-deletion step for this reason. |
| **Chroma REGEN of existing images** (generate a new image on a keyable background instead of matting the existing one) | Rejected as a complete solution | Regeneration changes composition and still retains key-color contamination — it is a segmentation-reference experiment, not a source-preserving background-removal solution (`PLAN-bg-complete-solution.md`: "Reject every chroma candidate as a complete solution; retain the generated plate only as a possible topology proposal"). |

---

## Pitfalls
- **Skipping the edge-hygiene block.** This is the single highest-leverage
  prompt addition found this session (79–169 stray pockets → 1). Never omit it
  from routes A/C.
- **Treating `machine_pass=true` as approval.** It is `PENDING_HUMAN_REVIEW` by
  design. The user has rejected a machine-passing candidate before.
  Route E always ends at the Stage 4 STOP.
- **Wide `--correction-unlock-radius`.** Reopening too large a neighborhood
  around a correction stroke can silently re-break an already-correct nearby
  region. Start narrow (R≈24), widen only if needed, and re-run the gate after
  every radius change.
- **Using `images/edits` (or any regeneration) to "clean up" an existing
  finished illustration's background.** Both are rejected routes — matting
  the existing pixels (Route E) is the only source-preserving path.
- **Claim drift between summaries.** A route's status must cite primary
  evidence (an actual API response, a measured metric), never a prior summary —
  the gpt-image-2 row above flipped twice in one session until the raw API
  error was cited directly.

## Verification of this skill file itself
```bash
python3 -c "import yaml,sys; yaml.safe_load(open('skills/transparent-product-image-gen/SKILL.md').read().split('---')[1])" 2>/dev/null \
  && echo "frontmatter parses" || echo "check frontmatter YAML by hand (pyyaml may be absent)"
```

## Related skills
- [`element-edit`](../element-edit/SKILL.md) — for editing ONE element of an
  already-finished illustration; not for whole-background removal.
- [`svg-template-illustration`](../svg-template-illustration/SKILL.md) — if the
  transparent output must also fit an exact die-cut/SVG contour.
- [`learn-skill`](../learn-skill/SKILL.md) — the promotion mechanism this
  skill is gated behind (`proposed → trusted`).
