#!/usr/bin/env python3
"""falbatch.py — fan out N fal.ai jobs CONCURRENTLY via the QUEUE API.

Where falgen.py calls https://fal.run/<id> synchronously (one blocking request
per call, so N candidates take the SUM of all calls), this driver submits ALL
jobs at once through fal-client's async queue API (queue.fal.run) and awaits
them with asyncio.gather. Wall time ~= the slowest single call, not the sum.

Verified fal-client (1.0.0) async call shape:
    client = fal_client.AsyncClient(key=KEY)
    url    = await client.upload_file(path)                 # shared image -> URL (uploaded once)
    result = await client.subscribe(app_id, arguments, ...) # submit to queue + await result

Auth: reads FAL_KEY from .secrets/fal.env (never printed). Auth scheme handled
internally by fal-client (it expects the `<id>:<secret>` key string).

Concurrency: bounded by an asyncio.Semaphore (default 10) so we never exceed the
account's queue concurrency. Retry/backoff is bounded (default 3 tries, exp
backoff with jitter). Shared images named in a job's `upload` map are uploaded
ONCE up front and their returned URLs spliced into every job's arguments, so the
same crop is not re-base64'd / re-uploaded per job.

JOBS FILE (JSON list); each job is an object:
    {
      "endpoint": "fal-ai/sam-3/image",      # required: fal app id
      "arguments": { ... },                   # required: passed straight to subscribe()
      "out": "tasks/improve/_fb_taxi.png",    # required: where to save the first image
      "id": "taxi",                           # optional: label for logs
      "upload": {"image_url": "path/to.png"}, # optional: arg-name -> local path; uploaded
                                              #   once (shared across jobs via a cache) and
                                              #   the resulting URL injected into arguments
      "result_key": "masks"                   # optional: response list key to pull the
                                              #   downloadable URL from (auto-detected if omitted)
    }

INTERPRETER: requires `fal_client`, installed in .venv-gen (Python 3.12), NOT
the system python (3.9). Either invoke it directly with that interpreter:
    .venv-gen/bin/python scripts/falbatch.py --jobs jobs.json
or run `python3 scripts/falbatch.py ...` — the shim below auto re-execs under
.venv-gen/bin/python when fal_client can't be imported.

CLI:
    .venv-gen/bin/python scripts/falbatch.py --jobs jobs.json [--concurrency 10] [--retries 3] [--timeout 300]
    .venv-gen/bin/python scripts/falbatch.py --example          # print an example jobs.json and exit
"""
import argparse
import asyncio
import json
import os
import random
import sys
import time
from pathlib import Path

# --- interpreter shim -------------------------------------------------------
# fal_client lives in .venv-gen (Python 3.12), NOT the system python (3.9).
# If we're running under an interpreter that can't import fal_client, re-exec
# under .venv-gen/bin/python so `python3 scripts/falbatch.py ...` Just Works.
# Guard against an exec loop with FALBATCH_REEXEC so we only try once.
ROOT = Path(__file__).resolve().parent.parent
try:
    import fal_client  # noqa: F401  (probe + real import for the happy path)
except ImportError:
    _venv_py = ROOT / ".venv-gen" / "bin" / "python"
    if os.environ.get("FALBATCH_REEXEC") != "1" and _venv_py.exists() and \
            Path(sys.executable).resolve() != _venv_py.resolve():
        os.environ["FALBATCH_REEXEC"] = "1"
        os.execv(str(_venv_py), [str(_venv_py), str(Path(__file__).resolve()), *sys.argv[1:]])
    raise SystemExit(
        "falbatch.py needs the `fal_client` package, which is installed in "
        f"{_venv_py} (Python 3.12), not the current interpreter "
        f"({sys.executable}).\n"
        "Run it as:  .venv-gen/bin/python scripts/falbatch.py ...\n"
        "(or `python3 scripts/falbatch.py ...` — it will auto re-exec under "
        ".venv-gen if that venv exists)."
    )

import httpx


def load_key() -> str:
    """FAL_KEY from env or .secrets/fal.env. Never printed."""
    k = os.environ.get("FAL_KEY")
    if k:
        return k.strip()
    env = ROOT / ".secrets" / "fal.env"
    for line in env.read_text().splitlines():
        if line.startswith("FAL_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("no FAL_KEY (set env or .secrets/fal.env)")


def _resolve(p: str) -> Path:
    """Resolve a job path relative to repo root if not absolute."""
    pp = Path(p)
    return pp if pp.is_absolute() else (ROOT / pp)


def _extract_urls(result, result_key=None):
    """Pull downloadable file URLs out of a fal response (best effort).

    Handles the common shapes: {"images":[{"url":...}]}, {"image":{"url":...}},
    {"masks":[...]}, {"<key>": [...]} and bare URL strings.
    """
    out = []

    def grab(v):
        if isinstance(v, str) and v.startswith("http"):
            out.append(v)
        elif isinstance(v, dict) and isinstance(v.get("url"), str):
            out.append(v["url"])

    if result_key and isinstance(result, dict) and result_key in result:
        items = result[result_key]
        for it in (items if isinstance(items, list) else [items]):
            grab(it)
        if out:
            return out

    if isinstance(result, dict):
        for key in ("images", "masks", "image", "mask", "file", "files", "output"):
            if key in result:
                v = result[key]
                for it in (v if isinstance(v, list) else [v]):
                    grab(it)
        if not out:  # last resort: scan every value
            for v in result.values():
                for it in (v if isinstance(v, list) else [v]):
                    grab(it)
    return out


async def _upload_shared(client, jobs, uploads_cache):
    """Upload every distinct local path referenced by jobs' `upload` maps ONCE.

    Returns the cache {local_path: url}. Mutates each job's arguments in place,
    injecting the uploaded URL under the named argument.
    """
    wanted = {}  # local_path -> set of (job, arg_name)
    for job in jobs:
        for arg_name, local in (job.get("upload") or {}).items():
            wanted.setdefault(local, []).append((job, arg_name))

    async def up(local):
        path = _resolve(local)
        if not path.exists():
            raise FileNotFoundError(f"upload source missing: {path}")
        url = await client.upload_file(str(path))
        uploads_cache[local] = url
        return local, url

    todo = [local for local in wanted if local not in uploads_cache]
    if todo:
        results = await asyncio.gather(*(up(l) for l in todo))
        for local, url in results:
            print(f"[falbatch] uploaded shared {local} (1x, reused by {len(wanted[local])} job(s))")
    for local, targets in wanted.items():
        url = uploads_cache[local]
        for job, arg_name in targets:
            job.setdefault("arguments", {})[arg_name] = url


async def _download(url, out_path, http):
    out = _resolve(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    r = await http.get(url, timeout=120)
    r.raise_for_status()
    out.write_bytes(r.content)
    return out, len(r.content)


async def run_job(client, http, sem, job, retries, timeout):
    label = job.get("id") or job.get("endpoint", "?")
    endpoint = job["endpoint"]
    arguments = job.get("arguments", {})
    out_path = job["out"]
    result_key = job.get("result_key")

    async with sem:
        last_err = None
        for attempt in range(1, retries + 1):
            t0 = time.monotonic()
            try:
                result = await client.subscribe(
                    endpoint, arguments, client_timeout=timeout
                )
                urls = _extract_urls(result, result_key)
                if not urls:
                    raise RuntimeError(
                        f"no downloadable url in response: {str(result)[:300]}"
                    )
                saved, nbytes = await _download(urls[0], out_path, http)
                dt = time.monotonic() - t0
                print(
                    f"[falbatch] OK {label:>12}  {dt:6.1f}s  -> {saved}  ({nbytes} bytes)"
                )
                return {"id": label, "ok": True, "seconds": dt, "out": str(saved), "bytes": nbytes}
            except Exception as e:  # noqa: BLE001 - bounded retry on any transient failure
                last_err = e
                if attempt < retries:
                    backoff = min(2 ** attempt, 20) + random.uniform(0, 1)
                    print(
                        f"[falbatch] retry {label} ({attempt}/{retries}) after {type(e).__name__}: "
                        f"{str(e)[:160]} — backoff {backoff:.1f}s",
                        file=sys.stderr,
                    )
                    await asyncio.sleep(backoff)
        dt = time.monotonic() - t0
        print(f"[falbatch] FAIL {label}: {last_err}", file=sys.stderr)
        return {"id": label, "ok": False, "seconds": dt, "error": str(last_err)}


async def run_batch(jobs, concurrency, retries, timeout):
    key = load_key()
    os.environ["FAL_KEY"] = key  # fal-client also reads env internally
    client = fal_client.AsyncClient(key=key, default_timeout=timeout)
    sem = asyncio.Semaphore(concurrency)
    uploads_cache = {}
    async with httpx.AsyncClient() as http:
        await _upload_shared(client, jobs, uploads_cache)
        wall0 = time.monotonic()
        results = await asyncio.gather(
            *(run_job(client, http, sem, j, retries, timeout) for j in jobs)
        )
        wall = time.monotonic() - wall0
    return results, wall


def example_jobs():
    img = "tasks/nyc-taxi/work/L2_ctx.png"
    jobs = []
    for prompt, out in [
        ("yellow taxi", "tasks/improve/_fb_taxi.png"),
        ("window", "tasks/improve/_fb_window.png"),
        ("door", "tasks/improve/_fb_door.png"),
    ]:
        jobs.append({
            "id": prompt.replace(" ", "_"),
            "endpoint": "fal-ai/sam-3/image",
            "upload": {"image_url": img},
            "arguments": {"prompt": prompt},
            "out": out,
            "result_key": "masks",
        })
    return jobs


def main():
    ap = argparse.ArgumentParser(description="Fan out fal.ai jobs concurrently via the queue API.")
    ap.add_argument("--jobs", help="path to JSON list of jobs")
    ap.add_argument("--concurrency", type=int, default=10)
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=300.0, help="per-job client timeout (s)")
    ap.add_argument("--example", action="store_true", help="print an example jobs.json and exit")
    a = ap.parse_args()

    if a.example:
        print(json.dumps(example_jobs(), indent=2))
        return

    if not a.jobs:
        ap.error("--jobs is required (or use --example)")

    jobs = json.loads(_resolve(a.jobs).read_text())
    if not isinstance(jobs, list) or not jobs:
        raise SystemExit("jobs file must be a non-empty JSON list")

    results, wall = asyncio.run(run_batch(jobs, a.concurrency, a.retries, a.timeout))
    ok = sum(1 for r in results if r["ok"])
    print(
        f"\n[falbatch] DONE {ok}/{len(results)} ok  wall={wall:.1f}s  "
        f"(slowest job={max((r['seconds'] for r in results), default=0):.1f}s)"
    )
    if ok != len(results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
