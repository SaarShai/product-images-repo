# Image Generation — Tooling (subscription, no API keys)

How to actually **invoke** image generation in this repo, on any machine that has
the CLIs installed and logged in. This is the tooling reference; for the
iteration *process* see [`workflow.md`](workflow.md), and for skyline/template-fit
rules see the `skyline-template-illustration` skill.

Image generation here uses **local CLI tools backed by your subscriptions — no
API keys and no metered API calls.** Two providers:

| Provider | Tool | Backed by | Use |
|---|---|---|---|
| **OpenAI image model ("image 2")** | **Codex CLI** (`codex exec`) | ChatGPT subscription | **Default / priority** — whole-scene art + img2img edits |
| **Nano Banana (Gemini image models)** | **Antigravity CLI** (`agy`) | Google subscription | Testing, cheap iterations, the Gemini look |

> The plain **`gemini` CLI cannot generate images** (all image model IDs 404, no
> image tool). Use `agy` for Nano Banana.

Confirmed working 2026-06-17 by live tests. Commands assume `codex` and `agy` are
on `PATH` (the other device has Codex + Antigravity installed); `~` = home dir.

---

## Prerequisites / verify login

```bash
codex --version          # Codex CLI present
agy   --version          # Antigravity CLI present
```

- **Codex** must be logged into ChatGPT (`codex login` if not). Image generation
  works on the subscription when `~/.codex/auth.json` has `"auth_mode": "chatgpt"`
  — **no `OPENAI_API_KEY` is used**.
- **Antigravity** must be signed into a Google account — open the Antigravity app
  once to sign in if `agy` reports it's not authenticated.

---

## A) OpenAI "image 2" via Codex  (priority)

The Codex agent has a built-in image-generation tool. Drive it non-interactively
with `codex exec`.

**Text → image:**
```bash
codex exec 'Use your image generation tool to create an image: <ARTWORK PROMPT>. \
Save the PNG to <ABS OUTPUT PATH>.'
```

**Image → image (edit / restyle / localized change)** — preferred when changing
an existing picture; preserves composition well:
```bash
printf '%s' 'Use your image generation tool to edit the attached image: <WHAT TO CHANGE>. \
Keep the rest of the picture identical. Save the result PNG to <ABS OUTPUT PATH>.' \
  | codex exec -i <ABS BASE IMAGE.png> -
```

> ⚠️ **Footgun:** `-i/--image` is **variadic** — it greedily eats a trailing
> positional argument. **Always pass the prompt on stdin** (as above), never as a
> trailing string after `-i ...`, or the prompt is silently lost.

**Where output lands.** Codex also writes generated PNGs to
`~/.codex/generated_images/<session-uuid>/ig_*.png` (the UUID isn't known ahead of
time). Always instruct Codex to **save to an explicit absolute path** as the
primary capture; as a fallback, grab the newest:
```bash
ls -t ~/.codex/generated_images/*/ig_*.png | head -1
```

### Preferred repo wrapper: `scripts/subgen.py`

For repo tasks, prefer the wrapper over ad-hoc `codex exec`/`agy` calls:

```bash
python3 scripts/subgen.py --health
python3 scripts/subgen.py --provider openai --prompt-file P.md --out O.png -i base.png mask.png --timeout 420 --retries 1
python3 scripts/subgen.py --provider nano   --prompt-file P.md --out O.png -i base.png mask.png --timeout 420 --retries 1
```

`subgen.py` is the safer path because it kills timeout orphans, avoids
newest-image races, retries no-image results, validates the output image with
Pillow, and warns when Nano is likely to recompose tall references.

### Localized repair: bounded external redraw donor

When a finished illustration has a localized ghost/haze/smear artifact, or a
local semantic-continuity problem such as architecture that should continue
behind trees/foreground occluders, the best route may be a broader OpenAI edit
used only as a donor. The reliable sequence:

1. Bank the current best full-resolution image first.
2. Diagnose the actual visual failure in words before generating. Do not turn a
   semantic defect into a generic "clean haze" or "draw lines" patch.
3. Build an issue mask from the user-marked region or measured full-res boxes.
   For occlusion/continuity repairs, make the mask wide enough to include both
   the object and its occluder, so the model can redraw the relationship.
4. Generate with `scripts/subgen.py --provider openai`, attaching the banked
   image and mask.
5. Treat the raw provider output as a donor, not the final file. It may be
   lower resolution or over-edit the full image.
6. Resize/register the donor back to baseline dimensions if needed.
7. Composite only masked donor pixels back onto the banked baseline. Keep the
   generation/context mask separate from the final blend mask; the final mask
   may need to be tighter to avoid changing adjacent repeated structures.
8. For repeated architecture such as windows, floor grids, roof courses, or
   antenna shafts, define explicit preserve/guard zones and restore those zones
   from the banked baseline after the donor blend.
9. Verify changed pixels against the banked baseline, including protected-region
   checks for areas that must remain unchanged.
10. Show a board with conservative local repairs plus the bounded donor, because
   the broader donor can be visually best while still being mechanically safe.
   If the repair is subtle, include a marked crop or diff overlay; do not claim
   visual improvement the reviewer cannot identify.
11. If a user prefers a tight crop or raw donor tile, also show a larger context
   crop that includes the protected neighbor structure. A crop that hides the
   preserved windows/floors cannot prove the composite is safe.

Recorded example:
[Mask-Bounded External Redraw Donor](../wiki/concepts/mask-bounded-external-redraw-donor.md)
from the Berlin wave3 TV tower / foreground repair and Berlin wave6 bridge
stair-continuity repair, extended by the Berlin wave7 hotel-roof repair where
the raw donor looked best but the safe composite required floor-guarded final
blending.

---

## B) Nano Banana (Gemini) via Antigravity `agy`

Image generation is a built-in **tool** of the Antigravity agent — it is not a
top-level model, so `agy models` lists only the agent's text models, not an image
model. Drive it headlessly:

```bash
agy --dangerously-skip-permissions --add-dir <DIR> \
    --print "Generate an image: <ARTWORK PROMPT>. Save it to <ABS OUTPUT PATH>."
```

> ⚠️ **Flag order matters:** `--print` (alias `--prompt`) consumes the prompt as
> its value, so it **must be the last flag**. Put `--dangerously-skip-permissions`
> and `--add-dir` *before* it. `--add-dir` must include the output directory.

Notes:
- The specific Nano Banana variant (Nano Banana / Nano Banana Pro) is **not
  selectable per call** — the agent chooses. `agy` is for cheap/test renders.
- It can edit input images by referencing files inside the `--add-dir` directory.

---

## When to use which

- **OpenAI via Codex** — default for whole-scene artwork and img2img edits; strong
  composition preservation on edits. This is the priority route.
- **Nano Banana via `agy`** — testing, cheap iterations, and renders where the
  Gemini look is wanted.

## Constraint for template / SVG-fit tasks (skyline, baci-door, etc.)

Keep every generation prompt **artwork-only**. **Never** put template-geometry
words in a prompt — `SVG`, `contour`, `panel proportions`, `red zone`,
`blue separator`, `green line`, `orange arch`, `saloon-door guide`, `safe margin`,
`production stroke` — or the model reinvents the template. Geometry belongs to the
deterministic overlay/export step (`scripts/export_svg_template_fit.py`), not the
creative prompt. See the skyline skill's Template-Lock / prompt-boundary rules.

## Quick smoke test

```bash
# OpenAI via Codex
codex exec 'Use your image generation tool to make a single yellow circle on a white background. Save to /tmp/codex_test.png.'

# Nano Banana via agy
agy --dangerously-skip-permissions --add-dir /tmp --print "Generate a single yellow circle on a white background; save to /tmp/agy_test.png."
```
