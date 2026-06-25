```loop
name: berlin-bridge-crop-regeneration-two-round
topology: closed inner fleet
generator: prompt template agents plus scripts/subgen.py image generation providers
verifier: main orchestrator plus independent visual rubric agent and artifact validator
gate: python3 tasks/berlin-hotel-base/wave13_regenerate_bridge_crop/scripts/validate_outputs.py --manifest tasks/berlin-hotel-base/wave13_regenerate_bridge_crop/results/run_manifest.jsonl
stop: round 1 OpenAI and Nano outputs are recorded, round 1 is reviewed, 10 improved templates are written, round 2 OpenAI and Nano outputs are recorded, and final full-result options are shown to the user
budget: max_iterations=2, max_wallclock=90m
quorum: human user selects from final options; orchestrator review only shortlists
anchor_files: docs/image-generation.md, tasks/berlin-hotel-base/wave13_regenerate_bridge_crop/inputs/bridge_piers_work_crop.png, tasks/berlin-hotel-base/wave13_regenerate_bridge_crop/prompts/templates_round1.md
state_store: tasks/berlin-hotel-base/wave13_regenerate_bridge_crop/results/run_manifest.jsonl
recall: inspect state_store, generated outputs, and review notes before each round
writeback: append every provider run status, output path, prompt path, verifier verdict, and next action to state_store and review notes
state_concurrency: single_writer
stuck: same provider returns no image 2 times or two rounds show no visual improvement
advisor: prompt strategy subagents and provider guidance subagent, separate from verifier rubric
```
