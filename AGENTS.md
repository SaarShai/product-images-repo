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
images.

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

Skill bodies under `skills/<name>/` lazy-load on trigger. The names + 1-line
descriptions below are kept in this resident doc so a freshly booted (or
post-compaction) agent still knows what's available — so a model-invokable
trigger (e.g. `wiki-memory` for "have we done X") is recognised on sight
rather than re-derived from scratch.

### Slash-triggered (user types literally; model cannot auto-invoke)

These are literal text tokens you recognise yourself — NOT host-registered
commands. When the user's message starts with one of these tokens, load
`skills/<name>/SKILL.md` and follow it yourself, even if this host has no such
command installed (e.g. Codex, Antigravity) or shows an "unknown command"
error. Treat the rest of the message as the task. Don't improvise a hand-rolled
equivalent:

- `/think` — How an agent should think and approach problems — first-principles, reduce/simplify before adding, research-and-borrow before building, experiment-and-falsify, never hallucinate or flatter

### Model-invokable (host fires on matching context)

You don't need to dispatch these manually — but knowing they exist helps you
notice when context matches one (e.g. `wiki-memory` for "have we done X").

- `baci-template-fit-repair` — Use when working on tasks/baci-door, Baci door SVG template-fit, hex holes, hole-section scars, or image-generation repairs that must preserve a Screenery door template while fixing local cutout artifacts.
- `brainer-audit` — Use when the user explicitly activates Brainer audit mode, asks to audit this session, audit Brainer use, or track Brainer skill usage
- `cache-lint` — Audit a Claude Code project for prompt-cache hygiene against Anthropic's six cache rules (ordering, dynamic-content injection, tool stability, model switching, breakpoint sizing, fork safety)
- `caveman-ultra` — Terse output style
- `compliance-canary` — Use when a long session drifts — the single always-on drift watcher: one UserPromptSubmit hook combining a periodic skill-rule re-anchor (every N turns), symptomatic per-skill drift probes (filler creep, word-count growth, unverified done-claims, self-closing without asking, looping tool errors, rule fade), and a request ledger that keeps every user request OPEN until completed or the user closes it (so nothing the user asked for is silently dropped)
- `context-keeper` — PreCompact hook that extracts structured state (files, commands, errors, numbers, decisions, failures) from the transcript before compaction
- `element-edit` — Use when editing ONE element of a finished illustration while keeping the rest byte-identical — redraw / remove / restyle / reshape / move a single element inside finished watercolor+ink art (or any fixed image)
- `eval-gate` — Score AI output against a written rubric before it ships — an LLM-as-judge quality gate for content output (drafts, posts, answers) and product output (an agent's reply, an extraction, a generated payload)
- `index-first` — Prefer pre-built indexes over chains of grep/read/scan
- `lean-execution` — Prune plans, process, context, and delegation to the smallest safe path
- `learn-skill` — Turn a pointed-at source (local dir, doc URL, a workflow you just did, or pasted notes) into a reusable Brainer skill
- `loop-engineering` — Use BEFORE building any multi-step agentic loop, generator→verifier pipeline, fan-out/fleet, or iterate-until-correct/retry loop — INCLUDING an automated / unattended / scheduled / nightly process that regenerates, revises, or rebuilds artifacts and keeps retrying each until it passes a check, any self-correcting or "keep going until it's good enough" automation, and any build-and-verify or generate-and-grade pipeline
- `output-filter` — Use when terminal output is noisy with ANSI / progress bars / duplicate lines and you want to keep the agent's eyes on signal
- `plan-first-execute` — Plan before executing non-trivial or spec-worthy tasks
- `prompt-triage` — Use on every UserPromptSubmit (pre-model hook) to classify the prompt and emit a directive telling the main model which subagent/model should handle it
- `reference-style-packet` — Use when reference images must be turned into a visual style packet for image-generation agents, especially when previous outputs matched geometry but missed the actual art style.
- `requirements-ledger` — Use whenever the user states anything carrying intent — an ask, a question, a constraint, a preference, a compound "do X, Y, and Z" (one row per conjunct), or an implicit ask embedded in prose
- `result-vision-judge` — Use whenever judging/reviewing a generated illustration against a geometry template — by YOU or a sub-agent
- `semantic-diff` — AST-node-level diff for file re-reads
- `skyline-template-illustration` — Use when generating Screenery skyline or city-scape collections for the three-panel skyline template, including landmark allocation, saloon-door arch planning, run-through elements, top-contour adaptation, and vision review.
- `svg-geometry-style-illustration` — Use when an agent must produce an SVG-template-constrained illustration that both fits exact contour/cutout geometry and adapts to the actual attached reference image style
- `svg-template-illustration` — Use when a user gives an SVG template, dieline, contour, cutout layout, or Screenery panel plus style/color references and wants generated artwork to fit exactly inside the SVG contour while avoiding internal cutouts and keep-clear areas.
- `svg-template-review-judge` — Use when judging, reviewing, scoring, or deciding whether to accept, patch, or restart SVG-template-constrained illustration candidates.
- `svg-template-style-agent` — Use for agents that generate or transform visual elements from a reference-style packet before SVG geometry placement
- `task-retrospective` — Use only when the user explicitly activates task audit mode, asks for task-retrospective, says this task will repeat and should be learned from, requests an after-the-fact task learning audit, or types /retro
- `verify-before-completion` — Use before claiming work is done, fixed, passing, committed, or ready
- `wiki-memory` — Repo-local markdown wiki with progressive retrieval (search → timeline → fetch) and gated writes (verified facts only)
- `wiki-refresh` — Reconcile wiki-memory pages against the current codebase — Keep / Update / Consolidate / Replace / Delete drifted ones
- `write-gate` — Decide whether a candidate fact deserves persistent memory

### Durable memory store (`wiki/`)

This repo carries a curated knowledge store at `wiki/` — the *why/decision/
failure-lesson* layer (rationale, trade-offs, incidents, procedures), distinct
from auto-extracted code structure. Relevant when the task references past work,
prior decisions, or "have we done X". Query it before re-deriving: read
`wiki/L1_index.md` first, then `python3 skills/wiki-memory/tools/wiki.py search "<q>"`
→ `timeline` → `fetch`. Maintained by `wiki-memory` (write) and `wiki-refresh`
(reconcile vs code).

_Auto-generated by `./install.sh` — do not hand-edit between sentinels._
<!-- brainer:skills-catalog:end -->
