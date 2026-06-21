# J — Parallel fal.ai via the QUEUE API (`falbatch.py`)

**Status: PASS** — concurrent fan-out is **2.27x** faster than sequential on the
3-call SAM-3 test, and scales to ~`slowest_call` regardless of N.

## Problem

`scripts/falgen.py` calls `https://fal.run/<id>` synchronously, one blocking
HTTP request per candidate. Fanning out N candidates costs the **SUM** of all N
call latencies. We want it to cost ~the **slowest single call**.

## Solution

`scripts/falbatch.py` submits all jobs at once through `fal-client`'s async
**queue** API (`queue.fal.run`) and awaits them with `asyncio.gather`, bounded by
a semaphore (default concurrency 10).

### Verified `fal-client` (v1.0.0) async call shape

Confirmed against the installed package signatures (not just docs):

```python
import fal_client

client = fal_client.AsyncClient(key=KEY, default_timeout=300)

# Shared image uploaded ONCE -> URL string (not re-base64'd per job):
url = await client.upload_file("path/to/crop.png")

# Submit to queue + await the result (this IS the queue.fal.run path):
result = await client.subscribe(
    "fal-ai/sam-3/image",
    {"prompt": "yellow taxi", "image_url": url},
    client_timeout=300,
)
# result["masks"][0]["url"] -> download with httpx
```

Relevant verified signatures:
- `AsyncClient(key: str | None = None, default_timeout: float = 120.0)`
- `client.subscribe(application, arguments, *, with_logs=False, on_queue_update=None, client_timeout=None, ...)` → returns the JSON result dict
- `client.upload_file(path) -> str` (URL)

Auth: `fal-client` consumes the `<id>:<secret>` key string internally (it sets
the `Authorization: Key …` header itself) — we pass it via `AsyncClient(key=...)`
and also export `FAL_KEY`. **The key is read from `.secrets/fal.env` and never
printed.**

### SAM-3 endpoint schema (verified via fal docs)

- Input: `image_url` (required), `prompt` (text), `output_format`, `max_masks`…
- Output: `masks` (array; each item has a `url`), plus `image`, `metadata`,
  `scores`, `boxes`. `falbatch.py` pulls the first `masks[].url` (configurable via
  each job's `result_key`).

## Script: `scripts/falbatch.py`

- **Input**: `--jobs jobs.json` — a JSON list. Each job:
  `{endpoint, arguments, out, id?, upload?, result_key?}`.
  `upload` maps an argument name → a local path; falbatch uploads each distinct
  path **once** (deduped via a cache) and injects the returned URL into every job
  that references it — so a shared crop is never re-uploaded/re-base64'd per job.
- **Concurrency**: `asyncio.Semaphore(--concurrency)` (default 10) over
  `asyncio.gather`.
- **Retry/backoff**: bounded (`--retries`, default 3) with exponential backoff +
  jitter, capped at 20s.
- **Download**: each result's file fetched with a shared `httpx.AsyncClient`.
- **CLI**: `python3 scripts/falbatch.py --jobs jobs.json [--concurrency 10] [--retries 3] [--timeout 300]`
  and `--example` to print a ready-to-run jobs.json.
- Other scripts were **not modified**.

### Install

`fal-client` was installed into the existing uv-managed venv `.venv-gen`
(Python 3.12), which already has `PIL` + `httpx`:

```
VIRTUAL_ENV="$PWD/.venv-gen" uv pip install fal-client   # -> fal-client==1.0.0
```

## TEST (3 SAM-3 mask calls on `tasks/nyc-taxi/work/L2_ctx.png`)

Prompts: `["yellow taxi", "window", "door"]`. Harness:
`tasks/improve/_falbatch_test.py`. Sequential baseline = same queue jobs forced
serial (semaphore=1, awaited one-by-one).

| Mode                         | Wall time |
|------------------------------|-----------|
| Concurrent (queue, sem=10)   | **5.11s** |
| Sequential (one at a time)   | 11.59s    |
| **Speedup**                  | **2.27x** |

Per-job latencies were ~3.3–5.1s, so concurrent wall ≈ slowest call (5.1s) while
sequential ≈ the sum (11.6s). The gap widens with N.

Output masks (all non-empty, valid 1200x800 RGBA PNGs):
- `tasks/improve/_fb_taxi.png` — 241607 bytes
- `tasks/improve/_fb_window.png` — 27180 bytes
- `tasks/improve/_fb_door.png` — 54377 bytes

Assertions enforced by the test (all passed): every job ok in both modes; all
masks non-empty; `concurrent_wall < sequential_wall`.

A full CLI run (`--jobs`) was also exercised end-to-end: exit 0,
`wall=4.1s (slowest job=4.1s)`.

## PASS/FAIL: **PASS**
