# F-ops — making the image-editing LOOP faster, cheaper, more reliable

Research date: 2026-06-21. All facts verified against primary sources (fal/replicate
docs, GitHub repos) via WebSearch+WebFetch. Sources listed per item and at the bottom.

## Current state (grounded in the repo, not assumed)

- `scripts/falgen.py` and `scripts/falref_apply.py` are the ONLY two scripts that hit
  fal. Both call **synchronous** `https://fal.run/<id>`, **one image at a time**, with
  the image sent as a **base64 data URI** in the JSON body, `timeout=300`, no retry, no
  cache, no idempotency key.
- `fal-client` is **NOT installed** (`import fal_client` fails). `requests` is used
  directly. `torch==2.8.0` is installed and **MPS is available** (`torch.backends.mps.is_available()==True`).
  `diskcache` is **NOT installed**.
- The repo ALREADY has a strong deterministic-gate + fan-out harness for the
  subscription path: `run_matrix.py` (data-driven route matrix, ThreadPool for codex,
  serial for nano), `objective_gate_report.py` (geom+size hard gate, advisory dup count,
  judge packet), `geom_gate.py`, `dup_detect.py`, `svg_manifest.py`, `genbatch.sh`
  (own-pgroup supervised batch), `subgen.py` (subscription gen with pgroup-kill,
  race-safe discovery, retry, validation).
- So the GAP is specifically on the **fal/API path**: it has none of the queue/parallel/
  cache/retry/manifest discipline the subscription path already has. The biggest wins are
  to (a) move fal to the queue API + parallel fan-out, (b) add a content-addressed cache,
  (c) generate masks programmatically (SAM) instead of by hand — the #1 stated bottleneck.

---

## 1. fal.ai best practices (VERIFIED from fal docs)

### 1a. Queue API (`queue.fal.run`) is the RECOMMENDED path — not `fal.run`
- fal docs state plainly: **"asynchronous inference is the recommended way to call models on fal."**
- Endpoint format: `https://queue.fal.run/{model-id}`. `submit()` returns immediately with
  `request_id`, `response_url`, `status_url`, `queue_position`.
- Lifecycle: `IN_QUEUE` (has `queue_position`) → `IN_PROGRESS` (has `logs`) → `COMPLETED`
  (has `metrics.inference_time`). **"Requests in the queue are never dropped"** and the
  service **auto-retries failed requests up to 10 times** server-side (queue path).
- Sync `run` path: SDK retries up to 10 times **client-side**.
- A queued request can ONLY be dropped if you set `start_timeout` and the deadline expires
  before processing starts — otherwise it persists.
- Header `X-Fal-No-Retry: 1` disables retries; `priority: "low"` deprioritizes.
- **What to adopt:** switch falgen/falref to `queue.fal.run` via `fal_client.submit` (or raw
  POST to `queue.fal.run/<id>` then poll `status_url`/`response_url`). This is the
  foundation for parallel fan-out and survives the 10-concurrent throttle by queueing
  instead of erroring. **Effort S–M. Win: reliability (no dropped reqs, free retries) + throughput.**

### 1b. Concurrency & rate limits (VERIFIED)
- Default rate limit: **10 concurrent tasks per user** across all endpoints (one doc
  phrasing). The concurrency-limits doc: new accounts start at **2 concurrent**, self-serve
  scales to **40** based on paid invoices over the last 4 weeks; enterprise beyond that.
- **Requests are NEVER rejected for hitting the limit** — excess requests wait in queue and
  dispatch as a slot frees. So you can safely SUBMIT many at once; fal queues the overflow.
- Per-endpoint extra limits may apply on high-demand models independent of the account limit.
- **What to adopt:** fan out N candidates by submitting all of them to the queue, then poll/
  await; don't self-throttle below ~10. Treat the limit as "fire all, queue absorbs it."
  **Effort S. Win: throughput** (today we serialize; queue lets ~10 run truly concurrently).

### 1c. The official Python client `fal-client` (VERIFIED on PyPI)
- Current version **1.0.0**, `pip install fal-client`, Python ≥3.8.
- Methods: `run`/`run_async` (sync direct), `subscribe`/`subscribe_async` (queue-backed,
  auto-retry, returns final result), `submit`/`submit_async` (queue, returns a handle with
  `.status()`, `.get()`, `.cancel()`, `.iter_events()`), `upload_file()` (uploads to
  fal.media CDN → returns a URL), `encode_file()` (base64 data URL helper).
- Reads `FAL_KEY` from env automatically.
- Parallel: every method has an `_async` twin; standard pattern is
  `await asyncio.gather(*[fal_client.subscribe_async(id, args) for args in batch])`
  (verified asyncio.gather semantics: total wall-time ≈ the slowest single call, not the sum).
- **What to adopt:** replace hand-rolled `requests.post` with `fal-client`; use
  `subscribe`/`submit_async` + `asyncio.gather` for fan-out; use `upload_file()` instead of
  base64 data URIs (see 1d). **Effort S. Win: reliability + throughput + less code.**

### 1d. Stop sending base64 data URIs — upload once, reuse the URL
- Today falgen embeds the (resized) image AND mask as base64 in every request body. For N
  candidates over the same crop+mask, that re-encodes and re-uploads the same bytes N times,
  inflating request size and latency.
- `fal_client.upload_file(path)` uploads to fal's CDN once and returns a URL you pass as
  `image_url`/`mask_url`. Reuse across all candidates for that crop.
- **What to adopt:** upload crop+mask once per loop iteration; pass URLs to all fan-out
  candidates. **Effort S. Win: speed (smaller bodies, no re-upload) + cost (less egress).**

### 1e. Webhooks vs polling
- `webhook_url` on submit → fal POSTs `{request_id, status: OK|ERROR, payload}` on
  completion instead of you polling. Useful for a server; **for a local M3 CLI loop, polling
  `status_url` (or `subscribe`, which polls for you) is simpler** — no inbound endpoint to
  host. Note it for a future server build, don't adopt now. **Effort M (needs a listener). Skip for now.**

### 1f. Cost controls
- fal is pay-per-use; cheapest control is **don't call the expensive engine until a cheap one
  fails the gate** (see §5 cascade) and **cache** (don't pay twice for the same input). fal's
  own "metrics.inference_time" in the COMPLETED response lets you log per-call cost-proxy.
- **What to adopt:** log `metrics.inference_time` + endpoint into the run manifest so cost is
  attributable per engine; gate on cheapest-first. **Effort S. Win: cost visibility.**

---

## 2. Replicate (async/batch) — VERIFIED, relevant as a fallback provider

- `replicate` Python client supports webhook-on-complete instead of polling;
  `webhook_events_filter` selects `start|output|logs|completed`.
- **Idempotency / dedupe is an explicit doc recommendation:** "Webhook handlers should be
  made idempotent… handle potential duplicate webhooks by checking the prediction ID,"
  webhooks can arrive out of order, and "Replicate will retry the webhook a few times, so
  make sure it can be safely called more than once." This is the canonical reliability
  pattern to mirror (key by prediction/request id; ignore post-terminal events).
- No special batch endpoint — you submit many predictions and collect via webhook/poll, same
  shape as fal's queue.
- **What to adopt:** keep Replicate as a *secondary* hosted provider behind the same
  queue+cache abstraction; borrow its **idempotent-by-id** guidance for our own retry/cache
  layer. **Effort S (as guidance) / M (as a provider). Win: reliability + provider redundancy.**

---

## 3. OSS image-editing / agent pipelines worth borrowing (ALL repos verified to exist)

### 3a. IOPaint — `github.com/Sanster/IOPaint` (Apache-2.0) ⭐ HIGH VALUE for ERASE
- Image inpainting/erase tool. **Has a headless HTTP API server AND a batch CLI** (not just a
  web UI): `iopaint start --model=lama --port=8080` (server) and
  `iopaint run --model=lama --image=DIR --mask=DIR --output=DIR` (batch).
- Models: **LaMa** (the real eraser — exactly what GOAL.md says "only a real eraser works"
  for, vs flux-fill healing text/cars back), MAT, SDXL-inpaint, PowerPaint, BrushNet, AnyText.
- **Has a built-in Segment-Anything plugin** for interactive object segmentation + RemoveBG
  for foreground masks — i.e. it can DO the mask step too.
- **Explicit Apple Silicon support.** Runs fully local → **$0 per erase**.
- Caveat: repo was **archived (read-only) Aug 2025** — stable, still installable, no new
  features. License Apache-2.0 → fine to vendor/wrap.
- **What to adopt:** stand up a local IOPaint+LaMa server (or use its batch CLI) as the
  default ERASE engine; only fall back to fal Bria eraser when LaMa quality fails the gate.
  **Effort S–M. Win: cost (free local erase) + reliability (LaMa won't hallucinate objects back).**

### 3b. Segment Anything (SAM) — `github.com/facebookresearch/segment-anything` (Apache-2.0) ⭐ ATTACKS THE #1 BOTTLENECK
- GOAL.md: "MASK GENERATION is the #1 bottleneck — masks are eyeballed/coded by hand;
  this session wasted ~dozen iterations with coords ~100px off."
- SAM produces high-quality masks from **point / box / mask prompts** in ~4 lines:
  `predictor.set_image(img); masks,_,_ = predictor.predict(point_coords=..., box=...)`.
- **MPS-ready:** `device='mps' if torch.backends.mps.is_available() else 'cpu'` — and MPS IS
  available on this machine (verified). So a click/box → exact mask, no hand-coding coords.
- **What to adopt:** a `make_mask.py` that takes a click point or a rough box on the crop and
  returns a tight, feathered mask PNG → feeds falgen `--mask`. Kills the hand-coord workflow.
  **Effort M. Win: reliability (precise masks) + speed (no iterate-on-coords).**

### 3c. MobileSAM / FastSAM — VERIFIED (for speed if full SAM is heavy)
- **MobileSAM** `github.com/ChaoningZhang/MobileSAM` (Apache-2.0): swaps SAM's 632M ViT-H for
  a 5M Tiny-ViT; ~7× smaller, ~5× faster than FastSAM; "~3s on a Mac i5 CPU" → near-instant
  on M3 Max MPS. Drop-in `SamPredictor`-style API.
- **FastSAM** `github.com/CASIA-LMC-Lab/FastSAM`: YOLOv8-seg based, 50× faster than SAM,
  prompt-by-point/box/text.
- **What to adopt:** if SAM-H latency is annoying on M3, use MobileSAM as the predictor behind
  the same `make_mask.py` interface. **Effort S (swap checkpoint). Win: speed.**

### 3d. ComfyUI as an API — VERIFIED (medium-term, high power)
- ComfyUI exposes HTTP+WS: `POST /prompt` (queue a workflow in API-JSON → `prompt_id`),
  `/history/{prompt_id}` (results), `/upload/image`, `/view`, `/ws` (live per-node progress).
- The repo ALREADY has `scripts/comfy_build_workflow.py` + `scripts/comfy_run.py` — so this is
  partially wired. ComfyUI gives local SDXL-inpaint/ControlNet/IP-Adapter as a stable
  workflow-as-API instead of ad-hoc scripts.
- **What to adopt:** consolidate the local SDXL/ControlNet variants (controlnet_*_gen.py — there
  are ~6 of them) behind ONE ComfyUI workflow-as-API call. **Effort M. Win: reliability + maintainability (free local path stays one code path).**

### 3e. Krita AI Diffusion — `github.com/Acly/krita-ai-diffusion` (GPLv3) — borrow ARCHITECTURE not code
- Mature, ComfyUI-backed inpaint/outpaint/edit + ControlNet (incl. segmentation) + a separate
  AI-segmentation plugin for object select / bg-removal. Layered architecture: UI →
  orchestration → workflow logic → backend.
- GPLv3 → don't vendor into a permissive codebase, but **study its inpaint-region-selection and
  workflow-parameterization design** — it solves exactly our "select object → inpaint just
  that, change nothing else" problem at production quality.
- **What to adopt:** architecture reference for the mask→inpaint→composite contract; its custom-
  workflow JSON shows how to expose only the params that matter. **Effort S (read). Win: design quality.**

---

## 4. Reliability patterns (VERIFIED concepts + concrete shape)

### 4a. Content-addressed cache keyed by (image-hash, prompt, params) ⭐ HIGH ROI
- Industry pattern: SHA-256 over **decoded pixels** (format-independent) + prompt + sorted
  params = cache key; on hit, skip the call. Cited cost reductions 40–90% for repeat inputs.
- We re-run the SAME crop+prompt+seed constantly during iteration → big waste today (no cache).
- **Shape:** `key = sha256(pixels) + sha256(mask_pixels) + prompt + json(sorted params) + engine`;
  store `out.png` + the JSON manifest under `.gencache/<key>.png`. Check before any paid call.
  Use stdlib `hashlib` + a flat dir (no new dep), or `diskcache` (needs install) for eviction.
- **Effort S. Win: cost + speed (instant on repeat; near-zero risk).**

### 4b. Deterministic seeds
- falgen already accepts `--seed`; today it's optional/unused. Pin a seed per candidate so a
  re-run is reproducible AND cache-hittable. Record the returned `seed` (fal echoes it) in the
  manifest. **Effort S. Win: reliability + makes caching meaningful.**

### 4c. Retry/backoff + idempotency by request_id
- Queue path gives server-side retry; for the sync path or our own wrapper, add exponential
  backoff on 5xx/timeout. Borrow Replicate's rule: **key all retry/cache on a stable id**, and
  **ignore events after the terminal one**. Use `X-Fal-No-Retry` only when we want to fail fast.
  **Effort S. Win: reliability.**

### 4d. Structured run manifest (per call)
- Today falgen prints a one-liner and exits; provenance is lost. Emit one JSON per call:
  `{engine, endpoint, mode, seed, guidance, image_sha, mask_sha, prompt_version, request_id,
   inference_time, out_path, cache_hit, gate_result}`. `run_matrix.py` already writes a catalog
  for the subscription path — mirror that shape for the fal path so BOTH feed one audit/board.
  **Effort S. Win: reliability + cost attribution + auditability.**

### 4e. Snapshot / regression testing of the pipeline
- The deterministic gates (`geom_gate`, `dup_detect`, size-aspect, diffmask delta==0) ARE the
  regression oracle. Add a tiny fixtures set: a few (crop, mask, prompt, seed) inputs with a
  **frozen expected gate verdict** (geom PASS, delta==0, count==expected). A CI/pre-flight test
  re-runs them against cached outputs (no paid calls) and fails if a code change moves a verdict.
  The repo already has the test habit (`test_gen_safe.py`, `test_mine_transcripts.py`,
  `check_python_syntax.py`) and a flagged memory: "code gates need calibration on a 2nd candidate."
  **Effort M. Win: reliability (catch gate/compositor regressions for free, no API spend).**

---

## 5. Speed & cheapest-engine-that-passes (VERIFIED building blocks)

### 5a. Parallel fan-out is the single biggest throughput lever
- Today: sequential `requests.post`, one image at a time. With queue + `asyncio.gather`, N
  candidates run with wall-time ≈ the slowest one (verified gather semantics), and fal's queue
  absorbs anything over the ~10 concurrency limit. **Effort S–M. Win: throughput (≈Nx for N candidates up to the limit).**

### 5b. Local model warm-load (keep weights resident)
- localgen/SDXL/SAM reload weights per invocation (CLI = cold start every call). Run them as a
  **persistent local server** (ComfyUI for SDXL/ControlNet; a small Flask/`SamPredictor` daemon
  for masks) so weights load once and stay warm on MPS. Cold load of SDXL is tens of seconds;
  warm is the bottleneck-killer for the free path. **Effort M. Win: speed (free path), cost ($0).**

### 5c. Scout-cheap → finalize-big cascade (cheapest engine that passes the gate)
- Order engines by cost and STOP at the first that clears the deterministic gate:
  1. **Free/local first:** LaMa (IOPaint) for erase; local SDXL/ComfyUI for inpaint; SAM for masks.
  2. **Mid:** fal Bria eraser / Flux-fill (queue) only if local fails the gate.
  3. **High:** Flux.2 / Kontext / gpt-image for the hardest cases or the final hi-res pass.
- Run a cheap "scout" pass (small `--maxside`, fewer steps) to pre-screen prompts/masks; only
  promote gate-passers to a full-res final. The objective gate already exists to make this
  decision deterministic — wire it as the cascade's branch condition.
  **Effort M. Win: cost (skip paid calls when free passes) + speed (small scout first).**

### 5d. Right-size the payload
- Already resizes longer side to 1024 (`--maxside`); confirm scout uses a smaller side and only
  the final uses full res / `scripts/upscale.py`. Smaller input = faster + cheaper per call.
  **Effort S. Win: speed + cost.**

---

## RANKED top recommendations (biggest wins) + minimal adoption plan

### (i) THROUGHPUT — #1: fal queue API + parallel fan-out via fal-client
- **Why:** today every fal call is serial and sync; N candidates take N×. Queue + gather makes
  wall-time ≈ slowest single call; queue absorbs the >10 overflow with no rejections.
- **Plan (minimal):**
  1. `pip install fal-client` (verified pkg, v1.0.0).
  2. New `scripts/fal_queue.py` exposing `submit_many(jobs)`:
     ```python
     import asyncio, fal_client
     async def _one(job):
         return await fal_client.subscribe_async(job["endpoint"], arguments=job["args"])
     def submit_many(jobs):
         return asyncio.run(asyncio.gather(*[_one(j) for j in jobs], return_exceptions=True))
     ```
  3. Upload crop+mask ONCE with `fal_client.upload_file()`; pass the URL to every job (no base64).
  4. Have `falgen.py` route through this (keep the same CLI; swap the transport).
- **fal endpoint mode:** `subscribe_async` (queue-backed, auto-retry, returns final result).
- **Effort S–M. Expected win: throughput ≈ up to 10× for a fan-out; also reliability (server retries).**

### (ii) COST — #1: content-addressed cache + free-local-first cascade
- **Why:** we re-run identical (crop, mask, prompt, seed) constantly (cache → 40–90% fewer paid
  calls on repeats) AND we pay fal for erases LaMa can do for $0.
- **Plan (minimal):**
  1. `scripts/gencache.py`: `key = sha256(pixels)+sha256(mask)+prompt+json(sorted params)+engine`;
     check `.gencache/<key>.png` before any paid call; write through on success. Stdlib `hashlib`
     only (no new dep). Pin `--seed` so repeats are deterministic and hittable.
  2. Stand up **IOPaint+LaMa locally** (`iopaint start --model=lama` or its batch CLI) as the
     default erase engine; fall back to fal Bria eraser only on gate-fail.
  3. Make the engine order a cascade gated by `objective_gate_report.py`: local → fal-mid → fal-high,
     stopping at the first PASS. Log `metrics.inference_time` per call into the manifest for cost attribution.
- **Effort S (cache) + M (LaMa server + cascade). Expected win: cost (skip repeat + skip paid erase).**

### (iii) RELIABILITY — #1: SAM-driven masks + structured manifest + gate snapshot tests
- **Why:** mask generation is the stated #1 bottleneck (coords ~100px off, ~dozen wasted
  iterations); and the fal path has no provenance/regression safety net.
- **Plan (minimal):**
  1. `scripts/make_mask.py`: load SAM (or MobileSAM for speed) on **MPS**; input a click point or
     rough box on the crop → tight feathered mask PNG → feed `falgen --mask`. Kills hand-coded coords.
     ```python
     import torch; from segment_anything import sam_model_registry, SamPredictor
     dev='mps' if torch.backends.mps.is_available() else 'cpu'
     sam=sam_model_registry['vit_b'](checkpoint=CKPT).to(dev); p=SamPredictor(sam)
     p.set_image(img); masks,_,_=p.predict(box=box, multimask_output=False)
     ```
  2. Emit a per-call JSON manifest (engine, seeds, image/mask sha, request_id, inference_time,
     gate_result) mirroring `run_matrix.py`'s catalog, so fal + subscription paths feed one board.
  3. Add a fixtures regression test: a handful of (crop, mask, prompt, seed) with frozen gate
     verdicts; re-run against CACHED outputs (no API spend) and fail on any verdict drift.
- **Effort M. Expected win: reliability (precise masks end the coord-iteration loop; manifests +
  snapshot tests catch compositor/gate regressions for free).**

---

## Quick adoption order (highest ROI first)
1. **gencache.py** (S, cost+speed, zero risk) — do first; instant savings, no API change.
2. **fal_queue.py + upload_file** (S–M, throughput+reliability) — unlocks parallel fan-out.
3. **make_mask.py (SAM/MobileSAM on MPS)** (M, reliability) — kills the #1 bottleneck.
4. **IOPaint+LaMa local erase + cascade gate** (M, cost+reliability) — free, non-hallucinating erase.
5. **per-call manifest + gate snapshot tests** (M, reliability/auditability) — regression net.
6. Later/server-only: webhooks (fal/Replicate), ComfyUI workflow-as-API consolidation, Krita arch study.

---

## Sources (verified)
- fal queue/async: https://fal.ai/docs/model-apis/model-endpoints/queue
- fal sync: https://fal.ai/docs/model-apis/model-endpoints/synchronous-requests
- fal concurrency limits: https://fal.ai/docs/documentation/model-apis/concurrency-limits
- fal Python client (PyPI, v1.0.0): https://pypi.org/project/fal-client/
- fal client docs: https://docs.fal.ai/model-apis/client
- Replicate predictions/webhooks/idempotency: https://replicate.com/docs/topics/webhooks/receive-webhook , https://replicate.com/docs/topics/predictions/create-a-prediction
- replicate python client: https://github.com/replicate/replicate-python
- IOPaint (Apache-2.0): https://github.com/Sanster/IOPaint
- Segment Anything (Apache-2.0): https://github.com/facebookresearch/segment-anything
- MobileSAM: https://github.com/ChaoningZhang/MobileSAM
- FastSAM: https://github.com/CASIA-LMC-Lab/FastSAM
- ComfyUI server routes: https://docs.comfy.org/development/comfyui-server/comms_routes
- Krita AI Diffusion (GPLv3): https://github.com/Acly/krita-ai-diffusion
- asyncio.gather semantics: https://shanechang.com/p/python-asyncio-gather-explained/
