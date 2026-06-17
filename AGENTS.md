# Global agent rules (all codex sessions)

## Image-generation iteration: reset vs. patch

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

For any new SVG-template illustration task, use the repo-local skill at
`.codex/skills/svg-template-illustration/SKILL.md`. For acceptance, repair, or
restart decisions, use `.codex/skills/svg-template-review-judge/SKILL.md` and
actually inspect the artwork/overlay/debug images. A JSON or metric `PASS` is a
rejection gate only; it is not production approval.

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
