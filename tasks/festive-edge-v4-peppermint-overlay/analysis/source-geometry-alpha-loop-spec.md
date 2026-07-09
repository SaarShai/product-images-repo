```loop
name: festive-edge-v4-peppermint-overlay-source-geometry-alpha-inspection
topology: closed · inner · single
generator: main-agent-read-only-image-metadata-probe
verifier: separate-future-verifier
verifier_blind: true
verifier_inputs: exact commands, concise output lines, source PNG paths, raw lane report
gate: command `python3 tasks/festive-edge-v4-peppermint-overlay/analysis/probe_source_geometry_alpha.py` exits 0 and prints DIM, ALPHA, BBOX, COMPONENTS, and STYLED_TRANSPARENT_PIXELS lines
stop: raw findings report is ready for separate verifier review
budget: max_iterations=1
anchor_files: tasks/festive-edge-v4-peppermint-overlay/analysis/source-geometry-alpha-loop-spec.md, edge-v4-watercolor-piped-artwork.png, styled-v1-peppermint-artwork.png, styled-v1-peppermint-preview.png
state_store: tasks/festive-edge-v4-peppermint-overlay/analysis/
recall: read only the listed source images and task analysis folder; no production writes
writeback: optional analysis artifacts under tasks/festive-edge-v4-peppermint-overlay/analysis/ only
state_concurrency: single_writer
on_error: stop and report blocker with exact command output
output_actions: create_file max 3 allow tasks/festive-edge-v4-peppermint-overlay/analysis/**
```
