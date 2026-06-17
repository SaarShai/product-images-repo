# Berlin Skyline Imagegen Scout Verdict

Date: 2026-06-16

## Evidence Inspected

- Scripted scout board:
  `outputs/reviews/scout-tests/scout-tests-contact-sheet.png`
- Scripted scout report:
  `outputs/reviews/scout-tests/scout-test-report.md`
- Chat-displayed image-generation Scout A: three-route contact sheet.
- Chat-displayed image-generation Scout B: direct whole-scene control.
- Chat-displayed image-generation Scout C: strict red-zone guard.
- Scout prompts:
  `prompts/scout-test-imagegen-prompts.md`

## Verdict

`PROMPT RESTART / METHOD PIVOT`

The first A/B/C scripted placement boards and the stronger scripted scout board
are useful for inventory, but not strong enough as generation wireframes. They
remain visually faint and similar, and therefore do not prove which composition
route will become good final art.

The image-generation scouts are more useful. They show that a whole-scene
redraw can produce the desired Berlin watercolor/cohesive style, but direct
prompting is not reliable enough for red-zone and seam safety. The direct and
strict red-zone scouts still place recognizable train windows, building facade
detail, or landmark details on red/no-detail lanes.

## Decision Unlocked

Use a whole-scene redraw scout for style and cohesion, but do not trust the
raw image model output for production geometry. The next production path should
be:

1. Generate or select a cohesive whole-scene Berlin redraw route.
2. Use the SVG and red-zone map as a downstream hard gate.
3. Repair or mask local red-zone/seam conflicts deterministically where
   possible.
4. Ask the user to approve the strongest visual route before spending on final
   geometry/export work.

## Risks To Carry Forward

- Red vertical lanes can still cut train windows/doors.
- Hotel facade and lower podium details can land on red lanes.
- Brandenburg Gate columns/Quadriga can drift into the left red lane.
- Central Dom/church details can drift into red vertical lanes.
- The bridge arch is promising, but should be redrawn as part of the whole
  scene instead of pasted as a crop.

## Rule Learned

For skyline/city-scape tasks, faint lookalike placement mockups are not enough
to unlock full-generation work. Run proof-before-spend scout tests with
visibly different strategies, and treat any direct prompt that violates red
zones as a method signal, not as a candidate to polish blindly.
