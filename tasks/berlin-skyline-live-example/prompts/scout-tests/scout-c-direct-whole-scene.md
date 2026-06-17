# Scout C - Direct Whole-Scene

Attachment/input board:
- `/Users/za/Documents/product images repo/tasks/berlin-skyline-live-example/outputs/reviews/scout-tests/scout-c-direct-reference-board.png`

Goal:
Generate a rough whole-set Berlin skyline directly from the template and
references, without using a placement map. This tests whether direct prompting
has enough control.

Prompt emphasis:
- Use the three-panel Screenery skyline template structure shown in the board.
- Match the watercolor/pencil style and muted Berlin palette of the existing
  render reference.
- Include: Fernsehturm, Brandenburg Gate, Berliner Dom, Kaiser Wilhelm Memorial
  Church tower, Ritz-Carlton / Beisheim / Potsdamer Platz high-rise with lower
  podium/wing, Oberbaum-inspired bridge/viaduct arch, and yellow Berlin U-Bahn.
- Keep buildings/landmarks whole within their physical panels.
- Use white/paper-white sky; no blue sky fill.
- Avoid copying the old four-panel render layout literally; adapt it to the
  three-panel saloon-door template.

Pass if:
- It produces a coherent composition without needing a map.
- It includes the required landmark roster with acceptable placement.
- It respects the saloon arch and run-through U-Bahn premise.

Fail if:
- It drifts into a generic Berlin postcard, omits landmarks, crops focal
  features, or ignores the template structure.
