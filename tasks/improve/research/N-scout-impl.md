# N — scout.py: SCOUT-then-FINAL cheap-candidate picker

## Goal
Cut cost/latency on a single masked redraw. Instead of rendering N full-res
candidates (you pay N × full cost and discard N−1), generate N **cheap low-res**
candidates, pick the best with the judge, then render only the winner at full res.

## Design
`scripts/scout.py` — orchestrator only, **reuses existing verified tools** (no
re-implementation of generation or judging):

1. **SCOUT** — N cheap candidates in parallel. Calls `scripts/falgen.py`
   (`--mode fill` = masked inpaint = the "redraw" op) N times concurrently in a
   `ThreadPoolExecutor`, each with a small `--maxside` (default **768**) and a
   distinct `--seed` (`seed-base + i`). falgen's calls are blocking/synchronous,
   so the pool makes wall-time ≈ the *slowest* single call, not the sum.
   - Why falgen-concurrent, not `falbatch.py`: falbatch needs `fal_client`
     (not installed in the repo's resident `/usr/bin/python3` 3.9 env); falgen
     needs only `requests`, which IS installed. The task explicitly allows the
     "call falgen N times concurrently" path. scout still auto-detects an
     interpreter and would use any env that has the deps.
2. **PICK** — `scripts/sweep.py` (dedup via perceptual hash + pairwise VLM
   tournament via `scripts/judge.py`). scout parses sweep's
   `[sweep] WINNER: <path>` line to map the winner back to its seed.
   `imagehash` (sweep's dedup) is optional — sweep degrades to no-dedup; scout
   picks an interpreter with imagehash when available (uv `--with` fallback).
3. **FINAL** — re-render ONLY the winner's settings (same prompt + **same seed**)
   at `--final-maxside` (default **1400**).

**Outputs:** `<prefix>_c1..cN.png` (scouts), `<prefix>_final.png` (winner full-res),
`<prefix>_log.json` (candidates, seeds, winner, sweep stdout, timing).

**Safety:** secrets (FAL_KEY / OPENAI_API_KEY) are read only by the sub-scripts
from `.secrets/`; scout never reads or prints them. Per-gen `--timeout` bounds
each call; falgen itself retries inside its 300s request timeout. Failures are
staged: all-candidates-fail → exit 1, sweep/judge error → exit 2 (reported),
final render fail → exit 3, each with a written log.

## Script path
`scripts/scout.py` (only file created). Reuses `falgen.py`, `sweep.py`, `judge.py`.

## TEST (cheap, required)
```
python3 scripts/scout.py \
  --image tasks/nyc-taxi/work/L2_ctx.png \
  --mask  tasks/nyc-taxi/work/cabmask_ctx.png \
  --op redraw --n 3 \
  --prompt "a clean classic NYC yellow sedan" \
  --out-prefix tasks/improve/_scout
```

**Result: PASS.**
- 3 candidates generated concurrently @ 768×512 — `_scout_c{1,2,3}.png`.
  Per-gen: c1 41.1s, c2 19.2s, c3 49.2s; **scout wall = 49.2s** (= slowest,
  not the 109.5s sum → parallelism confirmed).
- sweep ran the dedup + pairwise tournament over 3 candidates and picked one:
  **WINNER = c1 (seed 1000)**. pick wall = 6.9s. No sweep/judge API errors.
- Winner re-rendered @ 1400 → `_scout_final.png` (1184×800). final wall = 42.2s.
- **Total wall = 98.3s.** Final is a clean watercolor+ink yellow sedan, no text.

## Time / cost saved
fal-noisy latency (full-res gen measured 26–42s across runs), so the durable win
is **compute/cost**, not wall:

| | scout (3 cheap + 1 full) | baseline (3 full-res) |
|---|---|---|
| pixels generated | 2,126,848 | 2,841,600 |
| relative compute | **0.75×** | 1.00× |

≈ **25% compute saved** at maxside 768 vs 1400 for this near-square crop. The
saving grows with N and with a smaller scout maxside (e.g. n=5 @ 512 → the N
discarded renders cost ~0.13× each instead of full). Wall-time win is real when
fal queue concurrency is limited (cheap gens finish faster and the slow full-res
pass runs once, on the winner only, instead of N times).

## Notes / limits
- `--op` currently maps only `redraw → fill`; extend `OP_TO_MODE` for kontext/eraser.
- Final output aspect follows the crop (falgen scales longest side to maxside).
- Cost model in the log is pixel-proportional (a fair proxy; fal bills per call,
  so the wall/queue win is the practical lever when concurrency is capped).
