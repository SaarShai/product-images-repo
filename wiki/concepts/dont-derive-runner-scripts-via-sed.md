---
schema_version: 2
title: "Don't derive runner scripts via sed: fragile and breaks silently"
type: fact
domain: dev-ops
tier: procedural
confidence: 0.85
trust: verified
created: "2026-07-12"
updated: "2026-07-12"
verified: "2026-07-12"
sources: ["transparent-clear-edge session 2026-07-12", "script derivation chain"]
resource: ""
supersedes: []
superseded-by: []
contradicts: []
tags: ["dev-ops", "scripting", "shell", "maintenance", "anti-pattern"]
---

# Don't derive runner scripts via sed: fragile and breaks silently

## Summary

**Generating runner script N+1 by sed-editing script N is a fragile anti-pattern.** Sed edits compound across derivation chains: a blank line inserted after a backslash continuation in script N triggers `syntax error near unexpected token '|'` in script N+1, yet the script launches silently with no output (no error log, no abort).

**Fix:** Write each new script fresh, or better: keep ONE parametrized runner template and pass arm list / round number as arguments.

## Trigger/symptom

- About to create script N+1 by sed/string-editing script N, or a similar derivation chain.
- A launched script's log stays empty; `bash -n script.sh` shows a syntax error near `|` or after a continuation backslash.
- Silent no-op launch; process completes but no work was done.

## Why This Matters

**Silent failure is invisible.** Sed edits to shell scripts can corrupt quoting, continuation lines, or conditionals without raising errors during derivation. The broken script launches, runs 0 commands, and exits cleanly. Hours of downstream waiting produces nothing.

**Fragility compounds.** Each sed derivation layer risks introducing new breakage. Debugging requires tracing back through multiple script versions to find where syntax broke.

## Implementation

**AVOID:**
```bash
sed 's/round3/round4/g; s/seed_list/...' run_round3.sh > run_round4.sh
# Backslash continuation in run_round3 may be mutated
# Blank line after continuation → syntax error in run_round4
```

**PREFER:**
```bash
# ONE parametrized runner, pass args
./runner.sh --round 4 --seed-list "$seeds"

# Or write the script fresh with explicit intent
cat > run_round4.sh << 'EOF'
#!/bin/bash
# [full script, not derived]
...
EOF
```

## Related

- [[index]]
