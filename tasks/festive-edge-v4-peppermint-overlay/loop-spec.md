```loop
name: festive-edge-v4-peppermint-overlay
topology: closed · inner · fleet
generator: main-image-builder
verifier: separate-asset-and-geometry-verifier
verifier_blind: true
verifier_inputs: task, source paths, output paths
gate: command: python3 tasks/festive-edge-v4-peppermint-overlay/verify_outputs.py exits 0 and reports both high-res options exist in production candidates, share edge-v4 dimensions, preserve non-object transparent background, and keep added decoration alpha inside the edge-v4 object mask.
stop: two production candidate PNGs pass verifier and visual inspection
budget: max_iterations=1
quorum: leader synthesizes read-only probe lanes plus separate verifier output
aggregate: leader synthesis after machine gate
anchor_files: AGENTS.md, tasks/festive-edge-v4-peppermint-overlay/loop-spec.md, production edge-v4 PNG, Styled V1 peppermint PNG
state_store: tasks/festive-edge-v4-peppermint-overlay/
recall: read loop-spec.md, source image metadata, ledger rows r23-a through r23-g, and prior styled-candidate-proof gate before each pass
writeback: record generated paths, verifier verdict, command output, and visual review notes under tasks/festive-edge-v4-peppermint-overlay/
state_concurrency: single_writer
on_error: stop and report blocker with exact command output
output_actions: create_file max 20 allow tasks/festive-edge-v4-peppermint-overlay/** and /Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/candidates/**
```
