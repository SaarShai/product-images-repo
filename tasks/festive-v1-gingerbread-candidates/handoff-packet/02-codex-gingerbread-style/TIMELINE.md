# Timeline

## Phase 1 - Initial Style Exploration

Started in primary session line 11 at `2026-07-08T18:00:21Z`. User asked for watercolor gingerbread-house style options for festive v1 artboard 2 cutouts, with strict inside-cutout containment and parallel subagents.

The session first treated the task as style/color/item exploration, then incorporated three screenshot references as the intended art style.

## Phase 2 - Concept Options And First Board

The agent fanned out concept lanes: watercolor style extraction, gingerbread/candy motif vocabulary, and cutout-aware composition routes. Early concepts included gingerbread facades, roof bands, windows/doors, icing garlands, peppermint disks, gumdrops, holly, and snow details.

This phase produced concept/board-style outputs but had a major semantic miss: too many options interpreted the cutouts as places for mini houses or architectural scenes.

## Phase 3 - Decoration-Only Correction

At `2026-07-08T18:25:04Z`, the user corrected the direction: the panels themselves are the gingerbread house walls/roof, and the cutouts should contain only decorations/candy. The agent generated a corrected decoration-only concept direction and board.

Accepted direction: decoration/candy/icing inside the contours, no houses/windows/doors/buildings/lettering.

## Phase 4 - Styled Image Failure

At `2026-07-08T18:39:47Z`, the user requested actual styled generated images. By `2026-07-08T19:14:52Z`, the user rejected the results as "not styled" and asked the agent to inspect previous project sessions to understand what styled means.

Failure: procedural or mechanically verified candidates passed geometry checks but did not satisfy project style. The project lesson became: style is visual provenance, not just deterministic shape/palette rendering.

## Phase 5 - Retrospective / Style Packet Lesson

At `2026-07-08T19:28:17Z`, the user asked for task-retrospective and fable-mode to identify why the oversight happened. The durable implication in-session was to use actual reference images/style packets, not prose-only or procedural approximations, when style fidelity matters.

## Phase 6 - Edge-V4 + Styled V1 Peppermint Overlay

At `2026-07-09T04:50:22Z`, the user provided the stronger base: `edge-v4-watercolor-piped-artwork.png` had good background, edges, style, and geometry. The task became adding items from `Styled V1 - Peppermint Icing Ribbons` inside each edge-v4 object while keeping edge-v4's background.

Supporting subagents verified the route: use `scripts/subgen.py --provider openai`/reference-attached image generation, edge-v4 as locked base/composition map, Styled V1 and style-packet contact sheets as motif/style references.

## Phase 7 - Style Refinement And Approved Direction

At `2026-07-09T05:25:39Z`, user clarified foreground items must match Styled V1. At `2026-07-09T05:41:57Z`, user approved the left option in a comparison screenshot and said later options drifted.

This made the left option the immediate style anchor for follow-up work.

## Phase 8 - Related Cleanup/Upscale Work In Same Session

The same Codex thread later drifted into related festive production tasks: magenta background border repair, upscale/blur diagnosis, M5 FAL crisp clean pilot selection, and applying/upscaling best magenta background images.

These are continuation context, not the core `Explore gingerbread style options` style establishment.

## Phase 9 - AB5 Cutout Continuation

The session later returned to cutout options for artboard 5 / AB5. The user wanted six cutout options with the same gingerbread background and icing border, then corrected that geometry-guide outputs still needed styling.

Additional corrections covered first-render viewing, avoiding ledger work, producing unmasked/uncropped images, and targeting the exact bottom-right semi-arched artboard 5 shape.
