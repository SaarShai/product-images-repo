# Interoperability: screenery-lean Integration

This repository generates production and print images for [screenery-lean](https://github.com/SaarShai/screenery-lean).

## Handoff Contract

**Output:** finished images land in the design's folder under the production-files root.
**Location:** same directory path as the corresponding `.ai` Illustrator file in screenery-lean.

Example: for `screenery-lean/designs/space/production/space-12mm-v8.ai`, output images go to `<this-repo>/designs/space/production/` and are copied/linked into screenery-lean for placement into the .ai file.

## Vendored Skills

Brainer skills in `skills/` are vendored from the canonical [Brainer](https://github.com/SaarShai/Brainer) repository.

- **Do not hand-edit** vendored skills here.
- Use `propagate` skill to sync updates from Brainer back to this repo after changes in the canonical repo.
- Check `skills/*/METADATA.json` to identify vendored vs. local skills.

## Query Escalation

For design-level decisions or geometry disputes with screenery-lean:
- Check `screenery-lean/CLAUDE.md` for its operating rules.
- Use the `judge` skill gate before claiming production readiness (AGENTS §7).
