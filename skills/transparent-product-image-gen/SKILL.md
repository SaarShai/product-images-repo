---
name: transparent-product-image-gen
description: Use when a product needs a NEW transparent-background (RGBA) illustration, an EXISTING illustration may be semantically regenerated with native alpha, or an existing raster must keep its exact pixels while its white/paper background is removed. Also use when a downstream tool needs a flat keyable background instead of alpha. Do NOT use luma/flood "punch" removal on watercolor art (it deletes real pale paint).
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
Must the output preserve the EXISTING raster's exact content and pixels?
├── YES → ROUTE E (correction-led matting + frozen gate + MANDATORY user review)
│         Do not regenerate: every generative route redraws some content.
│
└── NO → is a semantic redraw acceptable?
          ├── YES, based on an existing illustration → ROUTE A2 (ChatGPT Images
          │   native-alpha regeneration) + ROUTE B (split RGB/alpha upscale)
          └── This is a genuinely new illustration → ROUTE A1 (API-native alpha)
              + ROUTE B. Use ROUTE C only when the consumer needs a flat key
              color, OR when the art must be rendered by `gpt-image-2`
              specifically (which refuses `background=transparent` outright)
              → use ROUTE C-green, the verified default for that case.
```

STOP-and-ask-user points (do not proceed past these without explicit approval):
1. **After the first ROUTE A/C generation** — show the raw RGBA (composited on
   white/gray/black/magenta) to the user before spending more generations,
   batching, or promoting it. If an end-to-end proof was explicitly requested,
   one candidate-only upscale may run, but that does not approve the art.
2. **Before promoting any ROUTE E candidate out of `Images/candidates/`** — a
   machine `machine_pass=true` is `PENDING_HUMAN_REVIEW`, never final. The user
   has previously rejected a machine-passing candidate on native 1:1 review
   (see Pitfalls). Native-resolution review on white/gray/black/magenta is
   mandatory every time, no exceptions.

---

## ROUTE A — Native transparent generation or semantic regeneration

Do not conflate these two OpenAI surfaces:

- **A1, predictable API-native alpha for a new motif:** `gpt-image-1` with an
  explicit `background=transparent` parameter.
- **A2, best measured semantic regeneration of existing art:** ChatGPT Images
  2.0 in a signed-in browser, prompted for transparency. OpenAI documents that
  ChatGPT Images can make a background transparent. The successful PNG proves
  that the product returned genuine RGBA; neither its metadata nor the UI
  proves that the backend model ID was specifically `gpt-image-2`.

### ROUTE A1 — API-native alpha for a new image

**Model:** OpenAI `gpt-image-1`, `POST https://api.openai.com/v1/images/generations`,
`background=transparent`, `quality=high`, `size` matched to the image's aspect
(portrait product art used `1024x1536`). Returns a **real RGBA** image (not a
fake checkerboard).
Key: `.secrets/openai.env` (`OPENAI_API_KEY=...`), loaded the same way
`scripts/openai_edit.py` already does it (`scripts/_falcommon.py::load_openai_key()`).

### Mandatory edge-hygiene prompt block (verbatim — append to every A1/A2 prompt)

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

### New defect class — painted aura/glow (alpha gates miss it)

Native-transparent gens (both this API route and the A2 browser route) can
paint an **opaque glow/wash band** around the subject — a real halo of pigment
in the RGB, not a soft-alpha fringe — so alpha is near-binary and every alpha
check above (histogram, enclosed-pocket) passes clean while the glow is still
there. Gate it separately: `scripts/aura_gate.py`.
Append this anti-aura tail to any transparent-gen prompt (on top of the
edge-hygiene block, not instead of it):
```
isolated cutout on true transparency; transparent pixels begin immediately
outside the outermost painted or inked subject contour; all pigment and
paper-grain texture remain inside the subject silhouette only; no surrounding
watercolor wash, color bloom, glow, aura, halo, rim light, backlight, mist,
vignette, drop shadow, ambient color spill, or diffuse silhouette expansion;
flat ambient lighting; preserve soft watercolor texture inside the forms, but
no pigment outside them; only a 1-2 pixel antialiased transition at the
actual art edge.
```
Proved: eliminated the glow in the browser-lane run
`REVIEW/marine-bed-transparent/browser-lane/marine_browser_antiaura_s1.png`
vs earlier browser gens that had it.

### Exact runnable A1 command

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
(see Verification) and get user sign-off on style/composition before more
generations, batch work, or production promotion. A single reversible upscale
may remain in `Images/candidates/` only when the user explicitly requested an
end-to-end engineering proof; it is not approval of the art.

### ROUTE A2 — ChatGPT Images transparent semantic regeneration

Use a signed-in ChatGPT Images browser surface when retaining the subject,
style, and approximate composition matters more than pixel identity. Upload
the source (an ordinary RGB/white-background upload is sufficient) and use:

```text
Re-create the attached watercolor illustration as a NEW image in exactly the
same art style: loose watercolor with soft pigment blooms, delicate ink-line
detail, pastel palette. Reproduce ALL of the content, keeping composition,
colors and arrangement as close to the reference as possible. IMPORTANT:
generate it with a fully TRANSPARENT background (true alpha PNG) — no white,
no paper texture, nothing behind the subjects. The entire composition must sit
fully inside the canvas with a clear margin on all four sides; nothing may
touch or be cut off by any edge. Every object keeps clearly defined, fully
closed outlines.
```

The one-image fish/coral probe is at
`REVIEW/marine-bg-complete/fish-regen/fish_APP_s1.png`. Fresh verification:

- 1024×1536 RGBA, alpha 0–255 with all 256 values; exact A=0 is 66.7557%.
- No foreground touches the outer three-pixel canvas strips.
- Layout-mask IoU 0.8427 and global SSIM 0.7491 against the resized source;
  both beat the strongest API-native-alpha comparison candidates.
- It is still a redraw: branch, fish, bubble, and lower-coral details changed,
  and object saturation rose from 0.198 to 0.244.

OpenAI's product documentation calls this **ChatGPT Images 2.0** and says it
can make backgrounds transparent. Do not relabel an app result as the API
model ID `gpt-image-2`: direct API requests with that ID and
`background=transparent` returned HTTP 400.

**Extraction (solved this session):** in Claude Desktop's built-in browser,
fetch the asset blob in-page then trigger an `a[download]` click — the file
lands directly in `~/Downloads`; no base64-chunking workaround is needed.
Original asset URLs come from the backend's `backend-api/my/recent/image_gen`
(estuary content URLs; the same response carries `conversation_id`,
`message_id`, `model_slug` metadata). Verify alpha in-page via
`OffscreenCanvas` before downloading, so a bad gen is caught before it ever
touches disk.

**Model routing is UNSTABLE — treat every session as unverified until
re-checked.** The web app's host-model slug determines which image backend
you actually get, and it silently varies: a `gpt-5-6-pro` chat produced
style-degraded output the user rejected, while the good exemplars from
2026-07-07 ran under `gpt-5-4-thinking` (a model that retires 2026-07-23) and
the user's true-transparency exemplar ran under `gpt-5-3`. Pin the chat's
model via `?model=` and re-validate per session — do not assume today's
session uses the same backend as last week's. Because of this instability,
the API chroma route (Route C-green) is the more stable default whenever the
art must come from a specific, pinnable model.

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
- Verified on the A2 fish result at full scale: 1024×1536 → 8192×12288 RGBA;
  alpha MAE 0 / max error 0 and source SHA-256 unchanged. Evidence and the
  four-background review board are under the product's
  `Images/candidates/bg-gen-fish-regen-v1/x8-split/` folder.
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

### ROUTE C-green — chroma-key regeneration (VERIFIED default when gpt-image-2 must render the art)

`gpt-image-2` refuses `background=transparent` (HTTP 400, re-confirmed this
session). When the art must be rendered by `gpt-image-2` specifically, key
against **green (`#00FF00`)**, not magenta — measured bg↔art separation is
roughly **2x** magenta's (ΔE 11.5 vs 6.8) and 5.9-9 for azure variants; the
green background stays near-flat (94.6-97.2% of pixels within ΔE<3 of the
sampled fill) under every prompt style tested — prompt phrasing barely moves
uniformity (`REVIEW/marine-bed-transparent/chroma-lane/chroma_gates.json`).

**Gen:** OpenAI Responses API, async **background job** (not the sync
`images/generations` call) — sync connection dies at ~75s for
`quality=high` `1024x1536`; there is no `input_fidelity` param for this
surface (adding one is a 400). Attach the reference image. Prompt is the
minimal P1 style, verbatim:
```
solid flat uniform background exactly #00FF00, every background pixel
identical, no gradient, no vignette, no texture, no shadow, no glow; nothing
cropped at the edges
```
Full prompt variants tried:
`REVIEW/marine-bed-transparent/chroma-lane/PROMPTS.md`. Generator:
`REVIEW/marine-bed-transparent/chroma-lane/chroma_gen.py`.

**Key:** `scripts/chroma_key.py` — a
global Lab ΔE two-threshold alpha (enclosed pockets die by construction since
alpha is global, not flood-fill). Use `DE_OPAQUE=11`, **not 8** — 8 leaves a
visible green rim. Boundary unmix + despill are confined to the dilated
transition band only; interior bubbles/translucent regions are left
untouched.

**Upscale:** `scripts/chroma_key_upscale.py`
— nearest-RGB refill under `alpha=0` (so RealESRGAN never sees green), then
Real-ESRGAN x4 on RGB, Lanczos on alpha, recombine. Final proof:
`REVIEW/marine-bed-transparent/chroma-lane/final-candidate/marine_green_P1_keyed_x4.png`
(4096x6144).

**Verification:** the uniform frozen-source-mask harness at
`REVIEW/marine-bed-transparent/verify-matrix/verify_all.py`
(`verdict.json`/`VERDICT.md`) is the arbiter for any removal-method
comparison, not a one-off eyeball. In that harness, `chroma_key.py` was the
**only** method with 0 residual green pockets AND 0 deleted art pixels;
ImageMagick/ffmpeg naive chroma-key left 864-1559 green pockets; plain
BRIA/BiRefNet ML matting on the flat-green source deleted up to 18.7% of the
art (thin branches) — see Rejected routes below.

**Known bug to fix before relying on this at scale:**
`tasks/double-marine-bed-wrapper-batch/alpha_aware_upscale.py`'s donor
threshold of `1/255` lets unstable low-alpha RGB poison the refill during
upscale — use `chroma_key_upscale.py`'s dedicated refill instead of the
generic upscaler for chroma-keyed sources.

**Better unmix/despill formulas (advisor-reviewed, not yet implemented in the
checked-in script — apply by hand or patch `chroma_key.py` before the next
use):**
- Donor-regularized unmix instead of naive unmix:
  `F = (α·D + λ·F0) / (α² + λ)`, with `λ = [0.1·(1-α)]²` (D = donor/neighbor
  color, F0 = observed foreground-adjacent color). Naive per-pixel unmix is
  unstable as α→0; this regularizes toward the donor.
- Despill only in **OKLab chroma**, never a global green-channel clamp — a
  flat `G` clamp visibly damages true yellows in the art.
- Treat any painted-in color spill as a **bounded proposal**, not ground
  truth, when deciding how far to unmix.
- Gates worth keeping for any future chroma-key harness: recomposition error,
  bubble ring-vs-center alpha (checks despill didn't eat translucency),
  stratified deleted-art recall (by feature thinness, not just aggregate),
  and an x4-upscale hidden-RGB poison test.
  (Source: GPT-5.6 Sol Ultra advisor review, session scratchpad
  `advisor2_reply.md` — cite as advisor guidance, not yet measured in this
  repo's own harness.)

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
| **ChatGPT Images 2.0 in a signed-in browser** | **Accepted candidate for semantic regeneration; user review still required** | `fish_APP_s1.png` is genuine RGBA and the best measured regeneration-fidelity result. Model metadata is absent, so call it a ChatGPT Images result, not proven API `gpt-image-2`. |
| **Codex CLI/subgen subscription path** | Rejected for this task, probed live | Three transparent-edit canaries returned `no valid image`; two earlier renders were opaque checkerboards. The wrapper cannot pin the image model or `background` parameter. This does not invalidate the separate ChatGPT Images browser route. |
| **images/edits on existing art** (gpt-image-1, to reproduce/preserve an existing illustration on transparent bg) | Rejected, probed live | Hard server-side ~61.2s timeout (`RemoteDisconnected`, not a client timeout) at `quality=high` or `input_fidelity=high`, reproduced 100% of trials. Only `quality=medium` completes, and even then composition drifts — mean-abs-diff-RGB over the opaque region was **44.3–46.0/255** vs the source (a regeneration, not a pixel-preserving cutout), with inconsistent small-bubble survival (5–6 of 7 across 2 samples). |
| **Pure-luma flood/punch removal** (white-key style) | Rejected, real-world failure across multiple attempts | The "flood FG ∧ restore" family (and its `--pure-luma` threshold variants) repeatedly deleted real pale painted content — ultra-pale ghosts and residual fringe — while a proxy metric (`white_rim=0`) reported success; **the proxy metric directly contradicted user inspection** (`PLAN-bg-complete-solution.md`, "Known from prior work"). `assisted_bg_remove.py`'s production core deliberately contains **no** white/luma punch or edge-deletion step for this reason. |
| **Chroma REGEN of existing images, magenta/blue key** (generate on a keyable background, then key) | Inferior fallback vs A2 when A2 is available | It redraws content like A2 but additionally leaves key-color contamination and needs despill. In the fish comparison, native-alpha ChatGPT Images had cleaner edges and substantially closer composition than `gpt-image-2` + blue key. **Superseded for the `gpt-image-2`-forced case by Route C-green** — green, not magenta/blue, is the verified key color (see Route C-green). |
| **ImageMagick/ffmpeg naive chroma-key** on a `#00FF00` source | Rejected, measured | Left 864-1559 residual green pockets in the uniform frozen-source-mask harness (`REVIEW/marine-bed-transparent/verify-matrix/verdict.json`); `scripts/chroma_key.py`'s global Lab ΔE two-threshold method was the only one with 0 residual green and 0 deleted art. |
| **BRIA / BiRefNet ML matting** on a flat-green source | Rejected for this art class, measured | Deleted up to **18.7%** of the art (thin coral/branch detail) in the same harness — ML segmentation trained for natural-photo subjects treats thin painted branches as background. See `REVIEW/marine-bed-transparent/verify-matrix/VERDICT.md`. |

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
- **Calling semantic regeneration "background removal."** A2 is allowed only
  when redrawing is acceptable. Route E is the source-preserving path when
  exact existing content and pixels matter.
- **Claim drift between summaries.** A route's status must cite primary
  evidence (an actual API response, a measured metric), never a prior summary —
  the gpt-image-2 row above flipped twice in one session until the raw API
  error was cited directly.
- **Alpha checks alone miss painted aura/glow.** Because the alpha channel on
  a native-transparent gen is near-binary, an opaque glow band painted in the
  RGB passes every alpha check clean. Run `aura_gate.py` separately; don't
  assume "alpha looks fine" means "no visible defect."
- **Trusting web-app model routing to stay put.** The ChatGPT Images backend
  behind a given chat is not fixed — it silently varies by host-model slug and
  has degraded style quality mid-session. Pin `?model=` and re-verify per
  session; treat the API chroma route (C-green) as the stable default when the
  model matters.
- **`chroma_key.py` at `DE_OPAQUE=8`.** Leaves a visible green rim; the
  measured-good value is `DE_OPAQUE=11`.

## Process laws (re-affirm on every route)
- **One candidate → user visual gate → only then batch.** Never generate a
  batch before a single representative candidate has explicit user sign-off
  (this session's rediscovery: `tasks/double-marine-bed-wrapper-batch/WIKI-DRAFT-generation-first-transparency.md`,
  "Approve one before scaling").
- **Pixel-verify alpha immediately after every gen** (histogram + enclosed-
  pocket checks above) before doing anything else with the file.
- **Machine gates are proxies, not the arbiter.** A `machine_pass=true` or a
  clean chroma-key metric is necessary, never sufficient; user review at
  native resolution on white/gray/black/magenta decides.
- **Use a uniform frozen-source-mask verifier for any removal-method
  comparison** — comparing methods on different source images (or without a
  shared ground-truth mask) produces incomparable numbers. See
  `REVIEW/marine-bed-transparent/verify-matrix/verify_all.py`.
- **Generator ≠ verifier.** The model/script that produced a candidate must
  not be the same one that grades it as passing.

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
