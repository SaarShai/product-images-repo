# Maps authoring spec (PROMPTER format)

How to hand-author a process map under `maps-data/`. The compiler is `maps/build.js`
(source of truth). After editing, `node maps/build.js` regenerates `maps/data.js`;
the live dashboard (`node maps/serve.js`) shows it.

## Layout
- `maps-data/index.md` — registry. Frontmatter `maps: [slug, ...]` (menu order). Add new map slugs here.
- `maps-data/<map>/index.md` — a MAP. Frontmatter: `title`, `type: map`, `nodes: [slug,...]`, optional `edges:`, optional `frames:`, optional `kind: process|reference`.
- `maps-data/<map>/<node>.md` — a NODE. Frontmatter + a `# H1` + markdown body.

Do NOT write `nid:` — the build mints + writes it back. Omit it.

## Node frontmatter fields (all optional except title)
```
---
title: "Parse SVG"            # JSON-quoted
type: step                    # step | decision | subprocess-link | reference
x: 140                        # canvas position (int)
y: 300
icon: "📐"                    # optional, shown on card
summary: "one-line purpose"   # shown in info panel + tooltip
gate: "what must be TRUE to pass this step"   # machine-checkable check; renders as the gate
status: draft                 # draft | active | blocked | done
lane: "prep"                  # optional swimlane name
link_map: stage-1b-geometry-panel   # ONLY on type: subprocess-link → drills into that child map
tags: [svg, geometry]         # optional
---
# Parse SVG

Body markdown. Cite tools/docs/other-nodes with [[target|label]].
```

### Node types
- `step` — a normal process step. Most nodes.
- `decision` — a branch/gateway. Outgoing edges should have `label:` "Yes"/"No"/condition.
- `subprocess-link` — drills into a child map; set `link_map: <child-slug>`. (Used on the family TOP maps, rarely inside a stage.)
- `reference` — a knowledge/SoT node (a tool, a doc, a law). Use for "the tool that does this step" or "the rule that governs it".

## Edges (in the MAP's index.md frontmatter)
```
edges:
  - {from: parse-svg, to: classify-roles, label: ""}
  - {from: check-aspect, to: rebuild, label: "fail"}
  - {from: check-aspect, to: approved, label: "pass"}
```
`from`/`to` are NODE SLUGS (filename without .md). Optional: `label`, `bend: N`, `color: N`, `route: bezier|smoothstep`.

## Layout convention (keep it readable)
- Main flow left→right: first node x=140, each next +260. Main lane y=300.
- A decision's two branches: put the targets at y=180 and y=420.
- Reference nodes for a step: place just below their step (y +150), same x.

## Gates & status (the point of these maps)
- Every step that has a real check gets a `gate:` — quote the measurable condition (e.g. "outside-mask pixel delta == 0", "guide aspect == panel aspect").
- `status:` lets an agent mark progress: draft (not started) → active (working) → blocked → done. Agents update this as they execute; the user sees where the work is.

## Validation
After authoring: `node maps/build.js` must report your map with 0 `[warn]` for it
(an unknown type/status is auto-normalized + logged as `[fixed]` — avoid those).
Every edge `from`/`to` must reference a slug listed in `nodes:`.
