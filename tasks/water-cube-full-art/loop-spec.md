```loop
name: water-cube-full-art
topology: closed · inner · fleet
generator: built-in image-generation reference-attached whole-scene redraw
verifier: separate cold vision reviewer plus deterministic output checker
verifier_blind: true
verifier_inputs: original task, source render, generated candidate, final print master
gate: command: python3 ./tasks/water-cube-full-art/verify_output.py --candidate "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Water Cube/Images/candidates/Water-Cube-full-art-candidate-v1.png" --final "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Water Cube/Images/finals/Water-Cube-full-art-print-master.png" exits 0; cold reviewer must also return PASS on all visual criteria
stop: candidate and final pass the deterministic checker and cold visual verifier; otherwise stop after the capped targeted regeneration and report the failed criterion
budget: max_iterations=2
quorum: deterministic checker and one independent cold visual reviewer agree
aggregate: leader reconciles the machine evidence and blind visual verdict
anchor_files: AGENTS.md, tasks/water-cube-full-art/PLAN.md, tasks/water-cube-full-art/prompts/base.md, source render
state_store: tasks/water-cube-full-art/
recall: read PLAN.md, prompts/base.md, source image metadata, and the latest reviewer verdict before each generation
writeback: record generated paths, prompt, verifier verdict, dimensions, and visual review notes under tasks/water-cube-full-art/
state_concurrency: single_writer
on_error: transient generation failure may retry once; auth, permission, policy, or unexpected errors halt and surface; visual failure returns one targeted observation to the generator
output_actions: create_file max 12 allow tasks/water-cube-full-art/** and /Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/Marriott China/Water Cube/Images/**
```
