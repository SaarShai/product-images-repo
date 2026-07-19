# Global agent rules (all codex sessions)

## Image output location

ALWAYS save/copy result images to an `Images/` subfolder inside the folder the user points
to — typically the production folder where the `.ai`/`.svg` template lives (e.g.
`…/production files/<product>/Images/`), organized as `Images/finals/` + `Images/candidates/`.
The repo `tasks/<task>/outputs/` is the working copy only and need not hold images unless one
is used as a doc example. (user rule, 2026-06-24)

## Image-generation iteration: reset vs. patch

**How to invoke image generation** (which CLI / command) is documented in
[`docs/image-generation.md`](docs/image-generation.md): subscription-only routes,
no API keys — OpenAI "image 2" via the Codex CLI (`codex exec`, priority) and
Nano Banana via the Antigravity `agy` CLI. The plain `gemini` CLI cannot generate
images. **Authorized exception:** Route C-green v2 (`scripts/run_c_green_v2.py`)
and Route P (native alpha) call the OpenAI API directly with `OPENAI_API_KEY`
instead of a subscription CLI — user-approved exception, 2026-07-13, scoped to
transparent-background product art; see `docs/image-generation.md` for scope.
The subscription-only rule above stands for everything else.

When a result is imperfect or needs improving, do not assume the next step
should be another edit or repair pass on that same result. Treat the latest
output as evidence. Before continuing from it, consider whether the accumulated
feedback and task learnings should instead be folded back into the source prompt
and used for a fresh generation from the original references/templates.

Decide case by case. If revising the prompt would make the next attempt clearer,
cleaner, or less constrained by earlier mistakes, prefer restarting from that
revised prompt over trying to rescue the most recent output. If continuing from
the current result is still the better path, make that choice deliberately.

## Template-constrained illustration composition

For Screenery image panels with yellow dashed safe areas and internal cutouts,
do not create a generic rectangular/full-canvas illustration and then crop,
clip, erase, or mask it to the SVG outline. That produces art that looks chopped
to fit instead of designed for the part.

Start from the SVG contour and design the composition inside that geometry:
derive safe pockets, place modules/figures/pipes/details only inside those
pockets, route elements around internal cutouts before rendering, and use final
masks only as verification/export guardrails. A metric pass after clipping is
not enough; decorative element masks should already avoid cutouts and the outer
boundary before any final cleanup.

Separate geometry success from style success. If the geometry/template method
passes but the user says the style does not follow the references, do not keep
palette-shifting or restyling the same procedural sketch. Restart from a
reference-first composition because style lives in object vocabulary, simplicity,
lighting, and shape language, not just sampled colors.

When style has failed, do not ask the next image-generation agent to infer the
look from prose. Build a visual style packet from the actual reference images
with `python3 scripts/build_reference_style_packet.py tasks/<task>`, attach the
packet crops/contact sheets to the style agent, and have that agent generate
style-matched elements before any geometry agent places them.

If the best rough candidates already preserve the layout/geometry but still look
assembled, procedural, or collaged, stop polishing the placement pipeline. Feed
those roughs plus the style references/style packet into image generation as
composition inputs and ask for a whole-panel redraw/restyle. Then use the exact
SVG exporter/checker as the downstream geometry gate. For watercolor control
panels, explicitly request the successful edge language: dark blue rim, slight
bevel, soft inner shadow, pale edge highlight, and occasional subtle rim/lip.

If the user approves geometry/dimensions/location and asks only for style
adaptation, this is the same routing case: the approved geometry image is a
composition map and downstream gate, not a raster to locally repaint or texture.
Do not substitute locked-geometry scripts, packet-crop compositing, palette
shifts, or prompt-only attempts for the attachment-aware whole-panel redraw
method.

For any new SVG-template illustration task that must move from SVG geometry to
reference-style-adapted art, use the repo-local orchestration skill at
`.codex/skills/svg-geometry-style-illustration/SKILL.md`, then delegate
geometry work to `.codex/skills/svg-template-illustration/SKILL.md`. For
acceptance, repair, or restart decisions, use
`.codex/skills/svg-template-review-judge/SKILL.md` and actually inspect the
artwork/overlay/debug images. A JSON or metric `PASS` is a rejection gate only;
it is not production approval.

For skyline or city-scape three-panel collections, use the repo-local skill at
`.codex/skills/skyline-template-illustration/SKILL.md` and the source-of-truth
workflow at `docs/skyline-template-illustration-workflow.md`. The default
template is `assets/skyline/city-skyline template.svg` unless the user uploads
a replacement.

## Template-fit repair learning

For Baci-door or similar SVG-constrained image-generation work, recover from the
actual task folder and latest artifacts before generating again. Treat SVG
geometry as authoritative, including polygon cutouts, and verify with the local
parser/export tooling rather than screenshots or filenames alone.

For Baci-style hole-section repairs, use the repo-local skill at
`.codex/skills/baci-template-fit-repair/SKILL.md`. A template-fit `PASS` is only
the mechanical gate: still review the hole crop and full-frame export. When the
main artwork is good but the cutouts are scarred, prefer bounded local donor
repair plus exact SVG cutout cleanup over broad inpaint or repeated prompt-only
nudges.

## Retrospective learning

When user feedback corrects the workflow, when an experiment finally works after
multiple failed approaches, or at the end of a non-trivial image-generation
task, use the repo-local skill at `.codex/skills/task-retrospective/SKILL.md`.
Run its evidence-first retrospective before the final report so durable lessons
are written to the narrowest skill, workflow doc, or wiki page instead of being
left only in chat.

<!-- brainer:skills-catalog:start -->
## Repo-local trigger skills (resident at boot)

Skill bodies under `skills/<name>/` lazy-load on trigger; the 1-line
descriptions below stay resident so a freshly booted (or post-compaction)
agent still recognises a trigger on sight instead of re-deriving it.

### Slash-triggered (user types literally; model cannot auto-invoke)

Literal tokens you recognise yourself — NOT host-registered commands. If the
user's message starts with one, load `skills/<name>/SKILL.md` and follow it
yourself even if this host has no such command (e.g. Codex, Antigravity) or
shows "unknown command". Treat the rest of the message as the task; don't
improvise a hand-rolled equivalent:

- `/baton` — Drop/grab a verified session-handoff file — pass in-progress work to the next agent (future session, another window, codex) via .brainer/baton/
- `/brainer-audit` — Use when the user explicitly activates Brainer audit mode, asks to audit this session, audit Brainer use, or track Brainer skill usage
- `/brainer` — Use when the user explicitly says `/brainer` or asks to use any relevant Brainer skill: inspect the optional-method reference, select the smallest task-relevant set, and apply only exported methods or complete skill contracts as declared
- `/caveman-ultra` — Experimental/manual terse-output style retained for paired evaluation
- `/evidentiary-run` — Freeze-inputs evidentiary run to validate a released pipeline on a new subject class
- `/fable-mode` — Experimental/manual five-gate work discipline retained for paired evaluation
- `/lean-execution` — Experimental/manual lean-work protocol retained for paired evaluation
- `/learn-skill` — Experimental/manual skill-learning workflow retained for paired evaluation
- `/loop-engineering` — Experimental/manual loop-design workflow retained for paired evaluation
- `/plan-first-execute` — Experimental/manual planning protocol retained for paired evaluation
- `/prompt-triage` — Experimental manual router for paired evaluation
- `/requirements-ledger` — Experimental/manual visible requirements-ledger workflow retained for paired evaluation
- `/self-improvement-loops` — Govern loops that optimize their own agent machinery.
- `/standing-orders` — Experimental standing-directive probes retained for shadow telemetry and paired evaluation
- `/styled-candidate-proof-gate` — Gate styled generated image claims
- `/task-retrospective` — Use only when the user explicitly arms task audit mode: /retro, asks for task-retrospective, says this task will repeat and should be learned from, or requests an after-the-fact task learning audit
- `/team-lead` — Experimental/manual orchestration protocol retained for paired evaluation
- `/think` — How an agent should think and approach problems — first-principles, reduce/simplify before adding, research-and-borrow before building, experiment-and-falsify, never hallucinate or flatter
- `/transparent-product-image-gen` — Use when a product needs a NEW transparent-background (RGBA) illustration, an EXISTING illustration may be semantically regenerated with native alpha, or an existing raster must keep its exact pixels while its white/paper background is removed
- `/verify-before-completion` — Experimental/manual FULL verification workflow retained for paired evaluation
- `/wayfinder` — Experimental/manual decision-recovery workflow retained for paired evaluation

### Model-invokable (host fires on matching context)

No manual dispatch needed — but knowing these exist helps you notice a
context match (e.g. `wiki-memory` for "have we done X").

- `baci-template-fit-repair` — Use when working on tasks/baci-door, Baci door SVG template-fit, hex holes, hole-section scars, or image-generation repairs that must preserve a Screenery door template while fixing local cutout artifacts.
- `cache-lint` — Audit a Claude Code project for prompt-cache hygiene against Anthropic's six cache rules (ordering, dynamic-content injection, tool stability, model switching, breakpoint sizing, fork safety), plus a rule-7 tool-surface audit (resident-but-unused MCP servers)
- `compliance-canary` — Use when a long session may drift or needs verification-compliance monitoring
- `context-keeper` — PreCompact hook that extracts structured state (files, commands, errors, numbers, decisions, failures) from the transcript before compaction, so the summarizer can't silently drop facts; a SessionEnd hook also archives the raw transcript to .brainer/sessions/raw/ (git-ignored)
- `element-edit` — Use when editing ONE element of a finished illustration while keeping the rest byte-identical — redraw / remove / restyle / reshape / move a single element inside finished watercolor+ink art (or any fixed image)
- `eval-gate` — Score AI output against a written rubric before it ships — an LLM-as-judge quality gate for content output (drafts, posts, answers) and product output (an agent's reply, an extraction, a generated payload)
- `impact-of-change` — Use before committing or claiming work done to map a code edit to its blast radius — which symbols depend on the changed ones, plus a LOW/MEDIUM/HIGH/UNKNOWN risk score
- `index-first` — Prefer pre-built indexes over chains of grep/read/scan
- `moodboard-cobuild` — Co-build a collection's STYLE BIBLE with the user: harvest exemplars from existing assets, compose an axis-by-axis choice board (medium/palette/illustration-style required, plus COMPLETE-BUILDING and GEOMETRY-EMBRACE), run forced-choice verdicts, lock bible v1 with a style handle (medium_ref/palette_ref/style_ref), then validate uncertain axes with one cheap probe-tile round
- `output-filter` — Use when terminal output is noisy with ANSI / progress bars / duplicate lines and you want to keep the agent's eyes on signal
- `propagate` — Use when the user asks to propagate, sync, roll out, or push Brainer skill changes to the sibling/consumer repos (screenery-lean, product images repo, farey-hecke, PROMPTER, …) after work in the canonical Brainer repo, or asks to harvest lessons, reap lessons, or bring learnings back from a sibling
- `reference-style-packet` — Use when reference images must be turned into a visual style packet for image-generation agents, especially when previous outputs matched geometry but missed the actual art style.
- `region-map-guide` — Use when a generation must place several distinct elements in specific zones of a fixed die-cut/template panel, when per-element proportions keep coming back wrong (repeated regen/registration mismatch, art stretching, elements drifting), or when the user gives zone requirements ("door here, lamps there, nothing near the knobs") — build a semantic color-region map PNG (each flat color = one element's placement, avoid-zones as prohibitions) plus its auto-matched color→meaning legend prompt, feed map as image-1 + style ref + legend to the generator
- `result-vision-judge` — Use whenever judging/reviewing a generated illustration against a geometry template — by YOU or a sub-agent
- `security-oversight` — Use before committing or claiming work done to triage a code edit for INTRODUCED security risk — leaked secrets, dangerous sinks, untrusted deps, risky auth logic
- `semantic-diff` — AST-node-level diff for file re-reads
- `skyline-template-illustration` — Use when generating Screenery skyline or city-scape collections for the three-panel skyline template, including landmark allocation, saloon-door arch planning, run-through elements, top-contour adaptation, and vision review.
- `style-prompt-engineer` — Turn a requested art style (named by the user, or embodied in a reference image) into the best generation prompt sections + the right reference-image inputs
- `svg-geometry-style-illustration` — Use when an agent must produce an SVG-template-constrained illustration that both fits exact contour/cutout geometry and adapts to the actual attached reference image style
- `svg-template-illustration` — Use when a user gives an SVG template, dieline, contour, cutout layout, or Screenery panel plus style/color references and wants generated artwork to fit exactly inside the SVG contour while avoiding internal cutouts and keep-clear areas.
- `svg-template-review-judge` — Use when judging, reviewing, scoring, or deciding whether to accept, patch, or restart SVG-template-constrained illustration candidates.
- `svg-template-style-agent` — Use for agents that generate or transform visual elements from a reference-style packet before SVG geometry placement
- `wiki-memory` — Repo-local markdown wiki with progressive retrieval (search → timeline → fetch) and gated writes (verified facts only)
- `wiki-refresh` — Reconcile wiki-memory pages against the current codebase — Keep / Update / Consolidate / Replace / Delete drifted ones
- `write-gate` — Decide whether a candidate fact deserves persistent memory

### Durable memory store (`wiki/`)

Curated why/decision/failure-lesson layer at `wiki/`. Query before re-deriving
(e.g. "have we done X"): read `wiki/L1_index.md`, then
`python3 skills/wiki-memory/tools/wiki.py search "<q>"` → `timeline` → `fetch`.
Maintained by `wiki-memory` (write) / `wiki-refresh` (reconcile vs code).

### Code-craft directives (resident at boot)

Always-on rules for writing code — they apply on every coding turn, not only when
a skill happens to trigger:

- **Surgical diffs.** Smallest reversible change; touch only what the ask needs;
  match local style; never reformat code you didn't change. Justify every changed
  line by the task — revert "while I was in there" edits. (`lean-execution` covers
  this when invoked; this is the always-on copy. The `whitespace_only_edit` +
  `dependency-manifest-changed` `compliance-canary` probes enforce it mechanically.)
- **Failure-mode interrupt.** If mid-task you slide into scope-creep (Kitchen
  Sink), premature abstraction (abstract only on the 3rd repeat — rule of three),
  happy-path-only (error path ignored), or a fix cascading across files (Runaway
  Refactor) — STOP, restate the goal, narrow scope.

### Host capability matrix (honest degradation)

Host capability & degradation matrix (claude/codex/gemini): see
`docs/HOST_CAPABILITY_MATRIX.md` — the RULE still binds on a host lacking a
hook; enforce it manually.

_Auto-generated by `./install.sh` — do not hand-edit between sentinels._
<!-- brainer:skills-catalog:end -->

## Project rules (hand-maintained)

- **Transparent-background image work.** ANY task generating transparent-bg (RGBA)
  product art or removing image backgrounds: FIRST read
  `skills/transparent-product-image-gen/SKILL.md` and follow ITS decision tree
  (`tasks/transparent-bg-endgame/REPORT.md` is the evidence record, not a route
  selector). The tree routes by task, NOT by a single default: must the output
  preserve an EXISTING raster's exact pixels? → Route E (matting, never
  regenerate). Native-alpha-capable model acceptable (new art or semantic
  regen)? → Route P/A1/A2. ONLY when the art must be rendered by a model that
  lacks native alpha (`gpt-image-2`) or the consumer needs a flat key color →
  Route C-green v2, entry point `/usr/bin/python3 scripts/run_c_green_v2.py`.
  Never route an exact-pixel-preservation task into C-green — its green-purge
  step is destructive and deletes art. Never ML-matting on fine art; never ship
  without gate_battery + 12× NEAREST junction review. (corrected 2026-07-16;
  supersedes the 2026-07-13 "canonical pipeline" wording that skipped the
  decision tree)
- **Pipeline validation = evidentiary run.** Whenever validating a released
  pipeline on a NEW subject class, after a significant pipeline change, or
  before claiming "generalizes"/"validated": read and follow
  `skills/evidentiary-run/SKILL.md` (freeze inputs + acceptance criteria
  before execution, no mid-run rescue, FP-vs-real diagnosis, re-gate
  previously-FAILed artifacts after gate patches, hostile-precondition
  case, claim ceiling). Agent-triggered by this rule — the user should never
  need to type it. Record usage: `python3 skills/learn-skill/tools/telemetry.py
  record --skill evidentiary-run --outcome hit` (promotes to model-invocable
  after 3 clean uses). (user rule, 2026-07-17)
- **Image output location.** ALWAYS save/copy result images to an `Images/` subfolder
  inside the folder the user points to — typically the production folder where the `.ai`
  and/or `.svg` template lives (e.g. `…/production files/<product>/Images/`), organized as
  `Images/finals/` + `Images/candidates/`. The repo `tasks/<task>/outputs/` is the working
  copy only and need not hold images unless one is used as a doc example. (user rule, 2026-06-24)

### Task routing — enforceable (owner-ratified 2026-07-18)

Classify every task by two observable properties BEFORE acting:
- **SPEC'D?** a written spec states the root cause (fixes) or exact construction (features) — no semantic invention needed. "Figure out why X" is NOT a spec.
- **GATED?** success verifies mechanically (tests, geometry gates, sha256, residuals) without judgment.

| Task state | Routing (MUST) |
|---|---|
| SPEC'D + GATED | Delegate to cheapest capable tier. Frontier models MUST NOT execute these beyond a ~30-line diff. |
| SPEC'D, not GATED | Delegate execution; a different agent verifies at the artifact layer before any "done" claim. |
| Not SPEC'D (diagnosis / semantics / design) | Frontier-tier work. Weaker agents MUST NOT attempt it — gather evidence, then escalate. |
| Not SPEC'D, fix <~30 lines, diagnosis IS the fix | Frontier does it directly; delegating is forbidden waste. |

Weaker-model agents (Sonnet/GLM/Terra/Luna/local):
- **W1** Ambiguous semantics, un-reproducible root cause, or new-machinery design → STOP. No best-guess implementation. Report BLOCKED or escalate to a frontier consult (frontier-advisor / codex high-effort / Kimi K3).
- **W2** Escalations MUST carry gathered evidence (measurements, file:line, failing output) — collecting it is your tier's job.
- **W3** Execute frontier-written specs verbatim; deviations → BLOCKED report, never silent judgment calls.

Stronger-model agents (Fable/Opus/Sol-class leads):
- **S1** Never forward a symptom: reproduce at the artifact layer, name the root cause, prescribe the fix with a borrow-checkpoint line (which existing standard solution applies / why none fits) BEFORE delegating. Delegating diagnosis is a malformed brief.
- **S2** Never execute spec'd+gated work >~30 lines yourself — delegate to the cheapest capable tier.
- **S3** Small judgment-dense fixes where the brief would exceed the diff: do directly, verify in the same turn.
- **S4** Un-codified semantics stay at frontier tier until banked (wiki/product model); execution lanes must quote the codified model.

- **B1 (borrow-checkpoint, all tiers)** Before building any NEW machinery (solver, cache, gate, build system, orchestration primitive, viewer subsystem), state in one line which existing framework/library/tool was checked and why it doesn't fit. A brief or plan that commissions new machinery without that line is malformed. The check may conclude "build" — demand the check, not the refusal (named failure class: Reinvented Wheel).
