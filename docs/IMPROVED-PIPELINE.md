# Improved image-editing pipeline — tool index

Built + verified in the 2026-06-21 improvement run. SOP: `skills/element-edit/SKILL.md`.
One self-checking command does most edits:

```
python3 scripts/edit.py --src IMG --op remove|redraw --element "the yellow taxi" [--box x0,y0,x1,y1] [--desc "..."] [--free]
```
It chains: automask → mask guardrail → routed engine → diff-mask pixel gate → perceptual leak gate →
OCR text gate → VLM judge → AUTO-REPAIR (erase stray text) → provenance JSON sidecar.

## Core tools (`scripts/`)
| tool | what | verified |
|------|------|----------|
| `automask.py` | text→tight mask (fal SAM-3) + cache | containment 0.857 |
| `mask_check.py` | pre-spend guardrail (containment/leak; exit2 fail) | 0.998 PASS / 0.000 FAIL |
| `edit.py` | one-command self-healing dispatcher | capstone SUCCESS |
| `falgen.py` | fal engines: fill / kontext / flux2edit / **eraser** (Bria) / fill `--cache` | — |
| `compose_fairy.py` | diff-mask composite + outside-mask pixel gate (==0) | — |
| `judge.py` | VLM verdict (check: text/defects; `--mode pairwise` quality) | text + pairwise OK |
| `text_gate.py` | deterministic OCR leftover-text gate (`.venv-ocr`) | TAXI conf1.0 |
| `leak_metric.py` | perceptual outside-mask leak (SSIM+LPIPS+DINOv2) (`.venv-metric`) | 0.0006 vs 1.0 |
| `lama_erase.py` | FREE local LaMa eraser (`.venv-iopaint`) | taxi removed |
| `qwen_edit.py` | Qwen-Image-Edit for TEXT (replace/render) | TAXI→CAB |
| `controlnet_sdxl_gen.py` + `measure_sdxl_cn.py` | exact SVG-contour fit (`.venv-gen`) | region-IoU 1.0 |
| `prompt_templates.py` | anti-reframe / no-text / prescribe-medium prompts | clauses verified |
| `gencache.py` | content-addressed cache (`--cache`, deterministic) | 0-API repeat |
| `falbatch.py` | fal queue parallel fan-out (`.venv-gen`) | 2.27× |
| `sweep.py` | dedup + pairwise tournament → best candidate | picks Flux.2 |
| `scout.py` | cheap low-res scouts → pick → hi-res final | −25% |
| `style_packet.py` / `dup_prefilter.py` | auto style-ref crops / near-dup pruning | 6 crops / hash16 |
| `gen_styled.py` / `erase_cascade.py` | ref-fed redraw / free→escalate erase | in-style / cascades |
| `eval_runner.py` | regression harness (`tasks/improve/eval/manifest.json`) | 4/4 green |

## Dedicated venvs (installs isolated to avoid conflicts)
- `.venv-gen` — diffusers/SDXL/ControlNet, fal-client (py3.12, MPS)
- `.venv-iopaint` — IOPaint+LaMa (free eraser)
- `.venv-metric` — torch/lpips/piq/DINOv2 (leak metric)
- `.venv-ocr` — PaddleOCR (text gate)
- system py3.9 — the fal/openai REST wrappers (falgen/automask/judge)

## Routing (don't re-derive)
remove → Bria eraser (`--free` = local LaMa) · redraw-in-place → Flux Fill · text → qwen_edit ·
restyle+layout → Flux.2/gen_styled · reshape → stretch-then-Kontext · exact geometry → controlnet_sdxl ·
same element ×N → consistency (reference-lock).

## Gates (always measured, never claimed)
pixel outside-mask delta ==0 · leak_metric < 0.06 (raise to ~0.12 for big-area erases) ·
text_gate no-text · judge pairwise for quality (absolute is lenient on loose art).
