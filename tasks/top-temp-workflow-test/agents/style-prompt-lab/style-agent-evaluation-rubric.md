# Style-Agent Evaluation Rubric

This rubric evaluates style-agent outputs only. It does not approve geometry
placement, SVG template fit, safe pockets, or cutout avoidance.

## Required Review Inputs

- the generated element sheet;
- the exact 6 to 10 packet crops attached to the style agent;
- the style exemplar sheet:
  `tasks/top-temp-workflow-test/style-packet/style-exemplar-sheet.png`;
- the source prompt variant used;
- the agent's provenance note.

## Scoring

Score out of 100.

| Criterion | Points | Pass Standard |
| --- | ---: | --- |
| Direct packet use | 20 | Elements visibly borrow from the attached crop images, not generic memory of watercolor panels. |
| Watercolor rendering | 20 | Granulation, bleed, soft highlights, shadow pooling, and paper-like color variation resemble the packet. |
| Object vocabulary | 15 | Dials, rails, capsule buttons, pins, bolts, and blue patches match the simple rounded control language in the packet. |
| Line and edge behavior | 15 | Outlines are blue, hand-painted, slightly uneven, and not uniformly vector-clean. |
| Isolation for handoff | 15 | Elements are separated, not arranged as a final panel, and can be cut or placed by a later geometry agent. |
| Efficient crop set | 5 | The agent used 6 to 10 relevant crops, not the entire 24-crop packet. |
| Negative constraints | 10 | No final SVG contour, diagonal slot, yellow safe area, labels, flat vector icons, photoreal metal, or glossy app UI. |

## Verdict Bands

- `REFERENCE-MATCH`: 85 to 100, with no critical failure.
- `PARTIAL`: 65 to 84, useful for limited extraction or further edit.
- `RETRY`: below 65, or any critical failure.

## Critical Failures

Any one of these forces `RETRY` even if the numeric score is high:

- the output is a final contour/template composition instead of isolated
  elements;
- the output appears to use only palette while missing packet linework,
  lighting, texture, and object language;
- controls look like generic UI widgets rather than parts from the packet;
- the output cannot be separated into reusable elements;
- the source note does not identify which packet crops were used.

## Suggested Review Form

```text
candidate:
prompt_variant:
attached_crops:
generated_artifact:

direct_packet_use: /20
watercolor_rendering: /20
object_vocabulary: /15
line_and_edge_behavior: /15
isolation_for_handoff: /15
efficient_crop_set: /5
negative_constraints: /10
total: /100
verdict:

best_elements:
weak_elements:
geometry_agent_handoff_notes:
retry_instruction:
```

