# Wiki Pages Index

Self-contained copies of selected repo wiki pages for the festive v1 gingerbread
handoff packet. Wiki originals were not edited.

## Included Pages

- `concepts/gingerbread-panel-cutouts-decoration-slots`
  - Title: Gingerbread panel cutouts are decoration slots
  - File: `concepts-gingerbread-panel-cutouts-decoration-slots.md`
  - Why included: Directly governs the festive gingerbread cutout task: no houses,
    windows, doors, painted text, or under-styled procedural previews inside
    cutouts; includes recent project-specific corrections about V1-style
    decoration density and every-instance checking.
- `concepts/illustrated-product-upscale-and-background-removal-workflow`
  - Title: Illustrated product upscale and background-removal workflow
  - File: `concepts-illustrated-product-upscale-and-background-removal-workflow.md`
  - Why included: Relevant to any downstream high-resolution transparent PNG
    delivery, sample-gated upscale/background-removal choices, hard-alpha checks,
    and image-output location conventions.

## Search Basis

Queried via `python3 skills/wiki-memory/tools/wiki.py search` for:

- `gingerbread`
- `festive`
- `styled`
- `upscale`

Only the two included content pages were high-relevance hits. Low-signal catalog
and log hits (`L1_index`, `index`, `log`) were not copied.

## Copied Prompt And Style Files

Verbatim source copies are under `prompts/`:

- `opt-h-brick-chimney-gingerbread-tree.md`
- `opt-tree-green-candy.md`
- `opt-tree-exact-silhouette.md`
- `styled-candidate-eval-rubric.md`
- `styled-redraw-v1-peppermint.md`
- `style-packet-README.md`
- `style-packet.json`

`style-packet.json` was copied in full because it was 32,259 bytes, below the
200KB summary threshold.
