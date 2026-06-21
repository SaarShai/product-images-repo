#!/usr/bin/env python3
"""Timed test: 3 SAM-3 mask calls concurrent (falbatch queue API) vs sequential.

Asserts concurrent wall-time < sequential wall-time and that masks are non-empty.
Run with the venv-gen interpreter:
    .venv-gen/bin/python3 tasks/improve/_falbatch_test.py
"""
import asyncio
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import falbatch  # noqa: E402

IMG = "tasks/nyc-taxi/work/L2_ctx.png"
PROMPTS = ["yellow taxi", "window", "door"]
OUTS = ["tasks/improve/_fb_taxi.png", "tasks/improve/_fb_window.png", "tasks/improve/_fb_door.png"]
ENDPOINT = "fal-ai/sam-3/image"


def make_jobs():
    return [
        {
            "id": p.replace(" ", "_"),
            "endpoint": ENDPOINT,
            "upload": {"image_url": IMG},
            "arguments": {"prompt": p},
            "out": o,
            "result_key": "masks",
        }
        for p, o in zip(PROMPTS, OUTS)
    ]


async def sequential(jobs):
    """Run jobs ONE AT A TIME on the same queue API (concurrency=1) — the
    apples-to-apples baseline for what falgen.py does today (sum of calls)."""
    key = falbatch.load_key()
    import os
    os.environ["FAL_KEY"] = key
    import fal_client
    import httpx
    client = fal_client.AsyncClient(key=key, default_timeout=300)
    cache = {}
    async with httpx.AsyncClient() as http:
        await falbatch._upload_shared(client, jobs, cache)
        sem = asyncio.Semaphore(1)  # force serial
        t0 = time.monotonic()
        results = []
        for j in jobs:  # await each before starting the next
            results.append(await falbatch.run_job(client, http, sem, j, retries=3, timeout=300))
        return results, time.monotonic() - t0


def main():
    # --- CONCURRENT ---
    print("=== CONCURRENT (falbatch queue, concurrency=10) ===")
    conc_results, conc_wall = asyncio.run(
        falbatch.run_batch(make_jobs(), concurrency=10, retries=3, timeout=300)
    )

    # --- SEQUENTIAL ---
    print("\n=== SEQUENTIAL (one at a time) ===")
    seq_results, seq_wall = asyncio.run(sequential(make_jobs()))

    # --- verify masks non-empty ---
    print("\n=== OUTPUT CHECK ===")
    all_nonempty = True
    for o in OUTS:
        p = ROOT / o
        sz = p.stat().st_size if p.exists() else 0
        ok = sz > 0
        all_nonempty = all_nonempty and ok
        print(f"  {o}: {sz} bytes {'OK' if ok else 'EMPTY/MISSING'}")

    speedup = seq_wall / conc_wall if conc_wall else 0
    print("\n=== RESULT ===")
    print(f"  concurrent wall : {conc_wall:.2f}s")
    print(f"  sequential wall : {seq_wall:.2f}s")
    print(f"  speedup         : {speedup:.2f}x")

    conc_ok = all(r["ok"] for r in conc_results)
    seq_ok = all(r["ok"] for r in seq_results)
    assert conc_ok, "some concurrent jobs failed"
    assert seq_ok, "some sequential jobs failed"
    assert all_nonempty, "some masks are empty/missing"
    assert conc_wall < seq_wall, f"concurrent ({conc_wall:.2f}s) not faster than sequential ({seq_wall:.2f}s)"
    print(f"\nPASS: concurrent < sequential ({conc_wall:.2f}s < {seq_wall:.2f}s), {speedup:.2f}x speedup, masks non-empty")


if __name__ == "__main__":
    main()
