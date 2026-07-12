# Clear-edge solid-background prompt experiment — task plan

## WHAT / WHY

Learn from the named failed sessions, then determine the best prompt structure and exact prompt snippets for generating reference-style illustrations with clean, clearly contrasted edges against a solid background. Test optional colored outlines / line art matching / color hold as one mechanism among several. Show controlled results to the user before each next round.

## Scope

- Audit the named Claude and Codex sessions plus their filesystem artifacts.
- Test prompt snippets with the uploaded coral reference, changing one variable at a time where generation routing permits.
- Compare prompt sections by their visible payoff: solid-background uniformity, contour continuity, edge contrast, interior-white separation, anti-aura behavior, and style fidelity.
- Show the image results and exact prompt deltas to the user; use feedback to select the next ablation.
- Update a reusable prompt-generation skill only after the prompt experiment yields stable evidence.

## Non-goals

- Do not remove backgrounds, key colors, matte images, create alpha, upscale, or promote finals in this redirected task.
- Do not batch-generate many product images before one representative proof is accepted.
- Do not overwrite or clean unrelated dirty-worktree changes.

## Load-bearing assumptions

- Similar redraws are acceptable experiment outputs; exact source preservation is not the experiment target.
- The useful design target is continuous, locally colored contour separation, regardless of whether a model recognizes “color hold,” “colored outlines,” or “line art matching.”
- User visual feedback is the acceptance oracle for style and prompt direction.

## Phases

1. Recover session evidence and map claims to actual artifacts.
2. Freeze the experimental rubric, prompt variants, and machine gates.
3. Generate the smallest discriminating prompt matrix and measure raw-image edge/background behavior.
4. Show results and exact deltas to the user; select the next single-variable round from feedback.
5. Bank only prompt snippets whose payoff survives controlled comparison and user review.

## Done means

1. A session-forensics report cites concrete transcript/artifact evidence for failures, successes, user feedback, and stuck points.
2. A prompt experiment report shows controlled variants and payoff measurements for contour closure, locally colored outlines, non-background whites, and anti-aura language.
3. Each result is shown with its exact prompt delta and a criterion-by-criterion visual verdict.
4. The user chooses a preferred direction or identifies a defect before another generation round.
5. A reusable prompt procedure is updated only after the selected snippets survive feedback and a repeat test.

```loop
name: transparent-coral-prompt-experiment
topology: closed · inner · fleet
generator: independent prompt-design and generation workers using the uploaded coral reference
verifier: fresh-context blind image verifier plus deterministic background-uniformity and aura measurements
gate: python3 scripts/aura_gate.py candidate.png && python3 skills/eval-gate/tools/eval_gate.py score --criteria-file tasks/transparent-background-workflow-v2/image-criteria.json --file tasks/transparent-background-workflow-v2/EXPERIMENT.md && human user selects the next direction
stop: prompt snippet payoff is attributable, results are shown, and the user selects or rejects the direction; otherwise stop at the budget cap and surface uncertainty
budget: max_iterations=2 per prompt arm and max_generation_candidates=8
quorum: deterministic gates pass and one cold vision verifier finds no blocking defect
anchor_files: AGENTS.md, tasks/transparent-background-workflow-v2/PLAN.md, tasks/transparent-background-workflow-v2/image-criteria.json, the uploaded coral reference
state_store: tasks/transparent-background-workflow-v2/EXPERIMENT.md
recall: read the plan, frozen criteria, experiment log, and named session evidence before each pass
writeback: append prompt, model route, output path, metrics, vision verdict, failure class, and next action after each pass
state_concurrency: single_writer
stuck: same failure class twice or two iterations without improvement
advisor: separate read-only divergent agent that does not verify the candidate
verifier_blind: true
verifier_inputs: original task, frozen criteria, candidate images, and deterministic metrics only
on_error: retry transient network errors at most twice; treat bad images as observations; interrupt on auth or configuration errors; halt and surface unexpected or policy errors
```
