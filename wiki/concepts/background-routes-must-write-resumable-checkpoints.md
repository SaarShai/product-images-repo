---
schema_version: 2
title: "Background routes must write resumable checkpoints"
type: concept
domain: "loop-engineering"
tier: semantic
confidence: 0.75
trust: partial
created: "2026-06-17"
updated: "2026-07-16"
verified: "2026-07-16"
sources:
  - "2026-07-16 dual-audit session"
  - "codex-task-polling.md (memory)"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - background-jobs
  - process-management
  - checkpoints
  - resumability
  - reliability
---

# Background Routes Must Write Resumable Checkpoints

## Summary

Any unattended or long-running background job (image generation batch, file processing, scheduled task) must checkpoint its progress to disk at regular intervals so that if the job dies mid-run, a restart can pick up where it left off instead of re-running the whole task.

## Core Rule

1. **Checkpoint to disk regularly** (every N items processed, every M seconds, after each major step).
2. **Checkpoints must be idempotent:** Running the job from a checkpoint produces the same final result as running from scratch (no duplicate outputs, no re-processing bugs).
3. **Log heartbeat:** Write a timestamp or status line to the checkpoint file / log each time you checkpoint. Do not rely on file mtime alone (it can be cached).
4. **Failure recovery:** On restart, always read the last valid checkpoint before resuming.

## Why

- **Quota limits:** Image generation APIs (FAL, OpenAI) have per-session rate limits; a job that dies halfway through has wasted quota and must re-run. Checkpoints let you resume without re-spending.
- **Long runs:** A multi-hour batch job can be interrupted by network loss, process kill, or sandbox timeout. Checkpoints make recovery transparent.
- **Debugging:** If a batch fails partway, checkpoints let you inspect partial results and tune parameters before re-running the rest.

## Related Lessons

- [[concepts/background-jobs-heartbeat-monitoring-and-sandbox-write-constraints]] — Companion lesson: how to monitor and detect failures in background jobs (heartbeat, Keychain crashes, sandbox write denials).

## Open Questions

- Should checkpoints use JSON (human-readable) or pickle (compact)?
- What is a reasonable checkpoint interval for a fast job (1000s of API calls/sec) vs. slow job (1 call per minute)?
- Should failed checkpoints be auto-archived or left for manual inspection?
