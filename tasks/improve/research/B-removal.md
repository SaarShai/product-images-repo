# B — Object Removal & In-Style Background Inpainting

**Goal:** remove an element (car, "TAXI" text, roof sign) from a finished watercolor+ink children's-book illustration and fill the hole with plausible IN-STYLE background (facade, road, plain yellow). PNG + mask (white = remove) → filled PNG.

**Date:** 2026-06-21 · **Host:** Apple M3 Max (MPS), torch 2.8.0, `mps True` verified locally · fal.ai + OpenAI keys present (`.secrets/fal.env`, `.secrets/openai.env`).

**Baseline finding (carried in):** `fal-ai/bria/eraser` already wired in `scripts/falgen.py` and works well. `fal-ai/flux-pro/v1/fill` (Flux Fill) is BAD at removal — it heals text back / invents new cars because negative prompts are weak. This research confirms WHY (see Best Practices) and finds the strongest alternatives.

> ⚠️ **falgen.py eraser bug (verify before relying on it):** in `scripts/falgen.py`, the `eraser` branch sets `body = {"image_url": ...}` and **never reaches** the `if a.mode in ("fill","eraser")` mask block in a way that builds a usable box mask — actually it does append `mask_url`, BUT the Bria endpoint requires `mask_url` and `mask_type` (default `manual`). Confirm the box-mask path actually produces white=remove and that `mask_type` is passed. This is the single highest-value fix in the current removal path.

---

## Why removal ≠ regeneration (the core mechanism)

Two failure modes documented in the literature, and they explain Flux Fill's behavior exactly:
- **Mask hallucination** — a diffusion inpainter generates spurious content inside the mask (a *new* car).
- **Mask-shape bias** — the inpainter fills the masked area with an object whose silhouette mimics the mask shape (car-shaped mask → it paints a car back).

A **dedicated eraser** (LaMa-class or Bria Eraser) is trained for *content-aware completion from surroundings*, not text-prompted generation, so it propagates the facade/road/sky INTO the hole instead of inventing a subject. This is the structural reason Bria Eraser beats Flux Fill here, and the reason LaMa is the OSS workhorse for removal.

Sources: [Mask Consistency Regularization in Object Removal (arXiv 2509.10259)](https://arxiv.org/html/2509.10259) · [Inpaint Anything (arXiv 2304.06790)](https://ar5iv.labs.arxiv.org/html/2304.06790)

---

## 1. Local / OSS (free, runs on this Mac)

### LaMa (advimman/lama) — the removal workhorse
- **URL:** https://github.com/advimman/lama · weights `big-lama`.
- **License:** Apache-2.0 ([LICENSE](https://github.com/advimman/lama/blob/main/LICENSE)). Weights have their own terms — verify the `big-lama` weight license for commercial use (research code is Apache; the released checkpoint terms are a separate line item — **flag: verify**).
- **What it is:** Fourier-convolution (FFC) GAN inpainter. Generalizes to ~2k resolution despite 256×256 training. Fast (sub-second on GPU). Best-in-class for REMOVAL on homogeneous/structured backgrounds (facades, roads, sky) — it does NOT generate prompted subjects, so it cannot "heal back" text or a car.
- **MPS:** Original repo is CUDA/CPU-oriented; MPS not first-class. Easiest MPS path is the wrappers below.
- **Mask convention:** white (255) = inpaint/remove.
- **Effort:** M (raw repo setup is heavier).

### simple-lama-inpainting (easiest local LaMa)
- **URL:** https://pypi.org/project/simple-lama-inpainting/ (v0.1.2, Jul 2023).
- **Install:** `pip install simple-lama-inpainting`. Downloads `big-lama` TorchScript weights on first run.
- **Usage:**
  ```python
  from simple_lama_inpainting import SimpleLama
  from PIL import Image
  s = SimpleLama()                 # respects torch device; set device for MPS (verify flag)
  img  = Image.open("crop.png")
  mask = Image.open("mask.png")    # white(255)=remove
  s(img, mask).save("filled.png")
  ```
- **License:** not stated on PyPI (**flag: verify** — underlying LaMa is Apache-2.0).
- **MPS:** not documented; TorchScript big-lama generally runs on CPU reliably and often on MPS. **Flag: test MPS, fall back to CPU** (LaMa is fast enough on CPU for our crop sizes).
- **Effort:** S. Best free path for a quick first pass.

### IOPaint (formerly lama-cleaner, Sanster/IOPaint) — RECOMMENDED local bundle
- **URL:** https://github.com/Sanster/IOPaint · docs https://www.iopaint.com/models
- **License:** Apache-2.0.
- **Status:** ⚠️ **archived / read-only since 2025-08-13**, last release **1.5.3 (2024-11-23)**. Still installable and fully functional; just unmaintained. (**flag: archived but usable.**)
- **Bundled erase models (confirmed):** **LaMa, MAT, MIGAN, LDM, ZITS, FcF, Manga** — plus diffusion editors (SD inpaint, PowerPaint, BrushNet, AnyText, InstructPix2Pix, PaintByExample, Kandinsky). For REMOVAL, use the **erase** family (LaMa default; MAT for hi-res detail; MIGAN smallest/fastest). FcF is fixed 512×512; ZITS slow on CPU.
- **MPS:** explicit Apple-Silicon support. CLI `--device=mps`; uses fp16 on MPS by default to save memory; `--no-half` if a model misbehaves; `--low-mem` available.
- **CLI / batch (this is the slot-in path):**
  ```bash
  pip3 install iopaint
  # batch: image folder + mask folder -> output folder (matches our PNG+mask flow)
  iopaint run --model=lama --device=mps \
    --image=/path/in_imgs --mask=/path/in_masks --output=/path/out
  # or interactive web UI:
  iopaint start --model=lama --device=mps --port=8080
  ```
  Mask convention: white = remove. The batch `run` command maps 1:1 onto our "PNG + mask → filled PNG" requirement with zero glue code.
- **Effort:** S–M (one pip install; first run downloads weights).
- Sources: [models](https://www.iopaint.com/models) · [install](https://www.iopaint.com/install) · [LaMa page](https://www.iopaint.com/models/erase/lama) · [PyPI](https://pypi.org/project/IOPaint/)

### MAT / ZITS / FcF (transformers, via IOPaint)
- **MAT** (Mask-Aware Transformer) — best for **large holes + hi-res detail**; good when the removed object is big (a whole car) and the surround has structure (windows, brick). Use via `iopaint run --model=mat`.
- **ZITS** — strong holistic structure but **wireframe module slow on CPU**; only worth it for strongly geometric backgrounds.
- **FcF** — good structure/texture but **fixed 512×512 only** → not ideal for our tall die-cut crops.
- Access all three through IOPaint (don't stand them up individually). Sources: [MAT](https://www.iopaint.com/models/erase/mat) · [ZITS](https://www.iopaint.com/models/erase/zits) · [FcF](https://www.iopaint.com/models/erase/fcf)

### Stable Diffusion inpaint / Flux Fill local
- SD-inpaint and PowerPaint/BrushNet run locally (incl. via IOPaint, MPS) but are **diffusion** → subject to mask hallucination / mask-shape bias → same "heals back" risk as Flux Fill. **Not recommended as the removal primitive.** Reserve diffusion only for the *replace-with-new-content* case, not clean removal. Flux Fill local has no advantage over the hosted Flux Fill we already rejected.

---

## 2. Hosted removal endpoints (paid, verified)

### fal.ai — Bria Eraser ✅ (current, confirmed working)
- **Endpoint:** `fal-ai/bria/eraser` ([API](https://fal.ai/models/fal-ai/bria/eraser/api)).
- **Inputs:** `image_url` (required), `mask_url` (required — binary mask of the area to clean), `mask_type` ∈ {`manual`,`automatic`}, default `manual`. Output: `{ image: { url, content_type } }` PNG.
- **Mask convention:** the area-to-clean mask; treat **white = remove** and verify on first call (fal docs don't state polarity explicitly — **flag: confirm polarity**).
- **Pricing:** ~**$0.04 / image** (per fal listing — **flag: confirm on dashboard**).
- **Mechanism:** Bria 2.3 foundation + Inpainting ControlNet, trained on licensed data (commercial-safe). Purpose-built eraser → does not re-prompt a subject back. **This is the proven hosted pick.**

### Replicate — allenhooo/lama ✅ (hosted LaMa, cheapest)
- **Endpoint:** `allenhooo/lama` ([page](https://replicate.com/allenhooo/lama)).
- **Inputs:** `image`, `mask` (white = inpaint/remove). Output: filled image.
- **Pricing:** ~**$0.00055 / run** (~1,800 runs/$1), ~3 s on T4. (**flag: needs REPLICATE_API_TOKEN — not currently in `.secrets/`.**)
- **Use:** hosted LaMa with no local setup — same removal quality as local LaMa, near-free. Good if we want LaMa quality without managing weights/MPS.

### Other hosted (noted, not adopted)
- fal `fal-ai/flux-pro/v1/fill` — already rejected (heals back).
- Bria also offers a full image-editing API (eraser, bg-replace) directly at bria.ai if we outgrow fal's wrapper.

---

## 3. Best practices to stop "healing back"

1. **Choose an eraser, not a generator.** The biggest lever. LaMa / Bria Eraser don't accept a subject prompt → they can't paint a car/text back. (This alone explains the Flux Fill failures.)
2. **Dilate the mask.** Morphological dilation (literature uses ~15×15 kernel) BEFORE inpainting — covers anti-aliased edges, soft ink halos, and the object's faint shadow/outline so no fragment survives to "seed" regeneration. We already feather; **add an explicit dilation step (grow white region by ~8–20 px) before feather.** Cheap, high impact.
3. **Avoid mask-shape bias.** A car-shaped mask invites a car. Erasers are immune; if a diffusion pass is unavoidable, reshape/round the mask and over-dilate so the silhouette carries no subject cue.
4. **Two-pass for in-style polish:** (a) **LaMa/Bria erase** → clean, content-aware fill (kills the object, no hallucination); then optionally (b) a **light img2img / Kontext pass at low strength** over only the filled patch to re-impart watercolor grain/ink texture if LaMa's fill looks slightly too smooth. Erase first, style second — never style-first.
5. **Negative prompts are weak on Flux Fill** (confirmed by our experience and the mask-shape-bias literature) — do not rely on "no car / no text" prose; rely on model choice + mask geometry.

Sources: [Mask Consistency Regularization (arXiv 2509.10259)](https://arxiv.org/html/2509.10259) · [Inpaint Anything (arXiv 2304.06790)](https://ar5iv.labs.arxiv.org/html/2304.06790) · [Attentive Eraser (arXiv 2412.12974)](https://arxiv.org/pdf/2412.12974)

---

## 4. Illustration-style preservation

- **LaMa preserves style intrinsically for removal:** it COPIES/propagates surrounding texture (the actual watercolor wash, ink lines, paper grain) rather than synthesizing new content, so the fill stays in-style by construction — *as long as the surround is reasonably homogeneous* (plain yellow, sky, a flat facade). This is its sweet spot for our task.
- **Failure case for LaMa:** large holes over highly *structured* backgrounds (windows, lettering on a building) can come out blurry/smeared. There, **MAT** (hi-res detail) or a **two-pass LaMa→light-Kontext-texture** finish is better.
- **Bria Eraser** replicates surrounding lighting/texture/visual harmony — strong on our illustrations and commercial-safe.
- **Avoid pure diffusion** for the removal step: it tends to render photographic or off-style content into a watercolor scene unless heavily conditioned — the opposite of what we want.

---

## RANKED top-3 for "clean in-style removal + background reconstruct"

1. **IOPaint (LaMa, local, MPS)** — free, Apache-2.0, batch CLI maps 1:1 to PNG+mask→PNG, runs on this Mac, no hallucination. Best default. *(archived-but-works; verify MPS or fall back CPU)*
2. **fal Bria Eraser** (`fal-ai/bria/eraser`) — proven, hosted, commercial-safe, ~$0.04/img. The reliable paid fallback when LaMa's fill is too smooth on structured surrounds. Already wired.
3. **Replicate allenhooo/lama** — hosted LaMa, ~$0.0006/run, near-free, identical removal quality to #1 without local setup. *(needs REPLICATE_API_TOKEN.)*

(MAT via IOPaint is the specialist for big holes over structured facades — use as a per-case swap, not the default.)

## Single best pick

**IOPaint with LaMa, local on MPS** — free, in-repo-friendly batch CLI, no "heal-back" by design, in-style by texture propagation. Keep **fal Bria Eraser as the paid fallback** for cases where LaMa smears a structured background.

## Minimal adoption plan

```bash
# 1) install once
pip3 install iopaint
# 2) erase: white=remove masks dir -> filled outputs (batch)
iopaint run --model=lama --device=mps \
  --image=/path/to/crops --mask=/path/to/masks --output=/path/to/filled
# fallback to CPU if MPS errors:  --device=cpu  (LaMa is fast enough on our crops)
```
Mask prep (add to our flow before erasing): **dilate white region ~12 px, then feather**, so ink halos/shadows are fully covered (prevents fragment-seeded regeneration). PIL: `mask.filter(ImageFilter.MaxFilter(25))` then GaussianBlur.

Paid fallback (already in repo) — fix + use the eraser branch in `scripts/falgen.py`:
```bash
python3 scripts/falgen.py --mode eraser --image CROP.png --out OUT.png --mask MASK.png
# ensure body includes mask_url (white=remove) AND mask_type="manual"; verify polarity on first call
```
Hosted-LaMa alt (if we add the key): Replicate `allenhooo/lama`, inputs `image`+`mask` (white=remove), ~$0.0006/run.

**Free-local vs paid:** #1 IOPaint/LaMa = **free** (local, MPS). #2 Bria Eraser = **paid ~$0.04/img**. #3 Replicate LaMa = **paid but ~$0.0006/img** (effectively free at our volume).

---

### Verification flags (do not treat as confirmed)
- big-lama / simple-lama **weight license** for commercial use — verify.
- simple-lama-inpainting **MPS** support — test; CPU fallback known-good.
- Bria Eraser **mask polarity** (white=remove) and **$0.04 price** — confirm on first call / dashboard.
- IOPaint repo **archived** (2025-08-13, last 1.5.3) — usable but unmaintained.
- Replicate path needs **REPLICATE_API_TOKEN** (not in `.secrets/` today).
- `scripts/falgen.py` eraser branch — audit that it actually sends a valid `mask_url` + `mask_type`.
