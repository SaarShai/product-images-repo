---
schema_version: 2
title: "Background jobs: heartbeat monitoring and sandbox write constraints"
type: fact
domain: "tools"
tier: semantic
confidence: 0.9
trust: audited
created: "2026-07-16"
updated: "2026-07-16"
verified: "2026-07-16"
sources:
  - "2026-07-16 dual-audit session"
  - "codex-task-polling memory entry"
  - "observed codex Keychain crashes and sandbox write denials"
supersedes: []
superseded-by: []
contradicts: []
tags:
  - codex
  - background-jobs
  - process-management
  - sandbox
  - automation
  - reliability
---

# Background Jobs: Heartbeat Monitoring and Sandbox Write Constraints

## Core Rules

### Rule 1: Heartbeat Monitoring Before Assuming Completion

**Do not assume a background job has completed or died without checking live status.** The companion status output ("running" / "done") is unreliable. Instead:

1. **Check log mtime:** Has the log file been modified recently (within expected task duration)?
2. **Read partial output:** Actually read the last 20–50 lines of the output file to see what the job is doing.
3. **Check process list:** `ps aux | grep <job_id>` to verify the process is still alive (if applicable).

**Companion status lies.** A job report that says "running" may have crashed; a job report that says "done" may still be mid-work on a slow step.

### Rule 2: Codex Keychain Crash in Agent Sandbox

**`codex exec` crashes with Keychain error (-50) when run inside the Agent sandbox.**

- **Error:** `SecItemCopyMatching returned -50 (internal error)`
- **Cause:** Agent sandbox denies Keychain access.
- **Fix:** Run codex from the **main shell** (not inside an agent subprocess).
- **Workflow:** If you need to spawn a codex job, do it from the user's main shell terminal, not from within an agent script.

### Rule 3: Codex Sandbox Write Denials

**Codex workspace denies `.git` writes** (commits, branch changes) from within the sandbox.

- **Error:** "Permission denied" or "cannot write to .git/" when running `git commit` inside codex workspace.
- **Fix:** 
  - **File edits by codex:** OK (codex rewrites files; sandbox permits this).
  - **Commits by codex:** Denied. Move commits to the main shell.
  - **Workflow:** Codex edits files; the user or a main-shell agent commits them.

## Evidence

- **Keychain (-50):** Observed across 3+ sessions in Agent context. Workaround validated: spawn codex from main terminal, it succeeds.
- **Status lying:** Codex companion status reported "done" while the actual job was still running (hanging on a slow network call). Reading the log mtime and partial output caught the stall.
- **Sandbox .git deny:** Multiple attempts to commit from codex-spawned script failed; committed from main shell, succeeded.

## Implementation

### For Background codex Job

```bash
# From main shell (not Agent sandbox):
codex exec --task-id <id> --wait &
CODEX_PID=$!

# In a monitor loop (or return early):
for i in {1..60}; do
  # Check log mtime
  LOG_AGE=$(( $(date +%s) - $(stat -f%m <log_file>) ))
  if [ $LOG_AGE -lt 30 ]; then
    echo "Job still active (log age ${LOG_AGE}s)"
  fi
  
  # Read partial output
  tail -20 <log_file> | grep -E "error|done|FAIL"
  
  sleep 5
done
```

### For File Edits + Commits

```bash
# Codex edits files (inside sandbox):
codex exec "cat file.py | sed ... > file.py"

# Main shell commits (outside sandbox):
git add file.py
git commit -m "Fix by codex"
```

## Related Lessons

- [[concepts/background-routes-must-write-resumable-checkpoints]] — Background jobs should checkpointable; this lesson adds monitoring discipline.

## Open Questions

- Should background-job orchestration be centralized (one `monitor.py` script for all background tasks)?
- How long should heartbeat monitoring wait before declaring a job dead?
- Should the Agent sandbox gain Keychain access in future versions, or is the "run from main shell" workaround permanent?
