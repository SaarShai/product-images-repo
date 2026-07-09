```loop
name: festive-magenta-m5-upscale-pilot
topology: fleet
mode: closed
generator: main-agent-local-m5-fal-pipeline
verifier: independent-readonly-agents-plus-python-verify-pilots
verifier_blind: true
verifier_inputs: "task, outputs"
gate: "command: python3 tasks/festive-magenta-m5-upscale/verify_pilots.py"
aggregate: "main verifier must pass the command gate and synthesize at least two read-only agent reports before presenting pilots"
stop: "pilot-ready-for-user-feedback"
budget: "max_iterations=1"
anchor_files: "/Users/za/.codex/memories/extensions/ad_hoc/notes/20260709T004015-0700-m5-fal-crisp-clean-preference.md"
state_store: "tasks/festive-magenta-m5-upscale/"
recall: "Use m5 FAL/Recraft crisp clean only as the preferred method, not as proof that any new file is correct."
writeback: "Only persist additional lessons if the user explicitly asks or task-retrospective is armed."
state_concurrency: "single_writer"
on_error: "Stop after the pilot pair and report exact failing file, command, and artifact path."
output_actions: "Write only task diagnostics under tasks/festive-magenta-m5-upscale/ and candidate images/boards under the pointed production Images/candidates folder."
```
