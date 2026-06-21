# O — Qwen-Image-Edit wrapper (fal.ai) — implementation + test

Status: **PASS**. Qwen-Image-Edit reached on fal, text replaced "TAXI" -> "CAB"
in the same lettering style, OCR verified.

## Why this engine
Qwen-Image-Edit is SOTA at *text inside images* — rendering/replacing specific
glyphs while preserving lettering style. Use it for the cases our other engines
(Flux Kontext / Flux Fill / nano / OpenAI) mangle or hallucinate text. It is a
TEXT specialist, not a general replacement for falgen.py.

## Endpoints (verified against fal OpenAPI, 2026-06-21)
- `fal-ai/qwen-image-edit` — whole-image instruction edit (default). "Has
  superior text editing capabilities." Pricing $0.03/megapixel.
- `fal-ai/qwen-image-edit/inpaint` — masked variant (requires `mask_url`,
  white = repaint). Used by the wrapper when `--mask` is given.

Auth: `Authorization: Key <id:secret>` (NOT Bearer), key from `.secrets/fal.env`.
POST to `https://fal.run/<endpoint-id>`. Local image sent as base64 PNG data URI.

## Schema — `fal-ai/qwen-image-edit` (edit)
Request:
| field | type | req | default |
|---|---|---|---|
| `prompt` | string | yes | — |
| `image_url` | string (URL or data URI) | yes | — |
| `image_size` | preset string or {width,height} | no | null |
| `num_inference_steps` | int 2–50 | no | 30 |
| `seed` | int/null | no | null |
| `guidance_scale` | number 0–20 | no | 4 |
| `num_images` | int 1–4 | no | 1 |
| `output_format` | "jpeg"\|"png" | no | png |
| `negative_prompt` | string | no | " " |
| `acceleration` | "none"\|"regular"\|"high" | no | regular |
| `enable_safety_checker` | bool | no | true |
| `sync_mode` | bool | no | false |

Response: `{ images:[{url,width,height,content_type}], timings, seed,
has_nsfw_concepts, prompt }`.

## Schema — `fal-ai/qwen-image-edit/inpaint` (adds)
Same as above plus required `mask_url` (string) and `strength` (number 0.01–1,
default 0.93). The wrapper sends a mask resized to the (post-maxside) image and
converted to RGB, matching the falgen.py fill convention (white = repaint).

## Script
`scripts/qwen_edit.py` — follows the falgen.py pattern:
- `load_key()` from `.secrets/fal.env` (never printed), `data_uri()` base64 PNG.
- CLI: `--image`, `--prompt` (or `--prompt-file`), `--out`, optional `--mask`
  (switches to the inpaint endpoint), plus `--maxside` (default 1536),
  `--seed`, `--guidance`, `--steps`, `--negative`, `--acceleration`.
- Downloads `images[0].url` to `--out`, prints `mode`, sent size, and seed.

Invocation used:
```
python3 scripts/qwen_edit.py \
  --image tasks/nyc-taxi/work/L2_ctx.png \
  --out tasks/improve/_qwen_cab.png \
  --prompt 'Replace the word "TAXI" on the car door with the word "CAB".
            Use the exact same lettering style, font, color, and size as the
            original "TAXI" text. Change nothing else in the image.'
```

## TEST result
- Input: `tasks/nyc-taxi/work/L2_ctx.png` (1200x800), taxi door reads "TAXI".
- Output: `tasks/improve/_qwen_cab.png` — **1248x832** (Qwen rounds dims to a
  multiple of ~16; not byte-aligned to the input frame, so OCR regions given in
  the original frame are ~1.04x off — scale before reusing original-frame coords).
- OCR gate (`text_gate.py`, PaddleOCR PP-OCRv6):
  - At the given region `405,492,728,592` (original frame): `found: ["CAB"]`,
    conf **0.9528**, exit 0. **No "TAXI".**
  - At the scaled region `421,511,757,615`: `found: ["CAB"]`, conf **1.0**.
- Eyeball: door now reads "CAB" in the same dark block lettering on yellow; rest
  of the scene (buildings, car body, roof TAXI light, wheels, street) unchanged
  and integrated (not a paste). Color crop: `tasks/improve/_qwen_cab_crop_color.png`.

VERDICT: **PASS** — text successfully replaced, style preserved, OCR reads "CAB"
(not "TAXI"). Note for downstream: Qwen may resize output; re-derive OCR/overlay
regions from the actual output dimensions, not the input frame.
