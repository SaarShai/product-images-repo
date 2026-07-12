---
schema_version: 2
title: "codex exec needs stdin closed: backgrounded process hangs"
type: fact
domain: dev-tooling
tier: procedural
confidence: 0.95
trust: user_verified
created: "2026-07-12"
updated: "2026-07-12"
verified: "2026-07-12"
sources: ["transparent-clear-edge session 2026-07-12"]
resource: "codex exec"
supersedes: []
superseded-by: []
contradicts: []
tags: ["codex", "cli", "backgrounded-process", "stdin", "process-management"]
---

# codex exec needs stdin closed: backgrounded process hangs

## Summary

**`codex exec` (Codex CLI non-interactive mode) blocks forever** when launched backgrounded without stdin redirect. The process remains idle, printing "Reading additional input from stdin..." to stderr; output file stays 0 bytes.

**Fix:** Always launch with stdin closed: `nohup codex exec ... </dev/null > out.txt 2>err.txt &`

## Trigger/symptom

- A backgrounded `codex exec` consult produces an empty output file.
- Process is idle, not consuming CPU.
- stderr shows `"Reading additional input from stdin..."`
- Process does not terminate.

## Why This Matters

Silent background process hangs waste compute time and delay downstream work. The model appears to be working but output never materializes. Empty output files mask the true failure mode (stdin blocking) and can break downstream pipelines that assume valid output.

## Implementation

**Wrong (hangs):**
```bash
codex exec -c system="analyze this" -c user="$input" > out.txt 2>err.txt &
```

**Correct (runs to completion):**
```bash
nohup codex exec -c system="analyze this" -c user="$input" </dev/null > out.txt 2>err.txt &
```

Key: `</dev/null` closes stdin so the process does not attempt to read additional input.

## Related

- [[index]]
