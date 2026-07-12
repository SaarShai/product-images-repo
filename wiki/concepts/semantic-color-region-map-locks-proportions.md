---
schema_version: 2
title: "Semantic color-region map makes generated proportions match the die-line"
type: concept
domain: "svg-template-illustration"
tier: semantic
confidence: 0.7
trust: asserted
scope: this-repo
created: "2026-07-12"
updated: "2026-07-12"
verified: "2026-07-12"
sources:
  - "/Users/za/Downloads/Wanderland-Packet-2026-07-11/05-scripts-and-logs/work-log_readable.md"
supersedes: []
superseded-by:
contradicts: []
tags: [region-map, geometry-guide, chatgpt, dieline, wanderland, gen-guide]
---

# Semantic color-region map makes generated proportions match the die-line

## Summary

Trigger/symptom: "generated proportions never match the die-line, registration always distorts" — or any generation where several distinct elements must each land in a specific zone of a fixed panel.

A SEMANTIC COLOR-REGION MAP fed to the generator makes generated proportions match the die-line, so that registration becomes a small clean transform (~5 percent distortion) instead of a fight. Five regenerations (v1–v5) failed because the guide under-specified per-element proportions, and registration-only alignment failed because forcing the door onto the cut stretched the art about 26 percent. The fix: encode the proportions in the guide itself as color zones.

Wanderland fire-station door (2026-07-08): the user directed the agent to a pre-existing color-annotated outline file and explained the color semantics in one message — grey = the 2 red door flaps with windows, black dots = area to AVOID putting windows (knob zone), orange = door arch, blue = lamps, green = fire logo, pink = facade/roof — instructing "ask chatgpt strictly follow the area generate a proportional image with the same style", and had the agent feed the color map + a prior version as style ref. **Provenance caveat:** the work log (a distillation of a 72MB raw transcript, per the packet README) shows the agent locating the file via `find` rather than creating it in that turn, so the annotated PNG already existed by then — the log does not establish HOW it was made (hand-painted by the user, prepared in an earlier untranscribed step, or by a collaborator). What's directly evidenced is that the user supplied the semantics and the strict-follow instruction. Result `doorpanel_regionmap_v1.png` was the session's best: every zone obeyed, aspect matched the cut (work-log 4784: "because the region map encoded the exact proportions, the door now matches the cut's aspect ratio").

Why it beats a plain grey-body guide (memory: geoguide-input-locks-aspect): the grey guide locks the OUTER aspect and focal placement; the color map additionally encodes PER-ELEMENT placement, size, and negative space (avoid-zones), because each color names one semantic region. A middle ground between prose (too loose) and ControlNet (needs API).

Registration corollary: once proportions are encoded in the map, register by PANEL bounds, not by detecting the element in the art — element detection over-catches (the door detector grabbed the brick arch), while panel registration lands the door correctly because its position already matches the map.

Direction pattern worth copying: the user supplied the missing reference as an ANNOTATED IMAGE rather than more prose — consistent with LAW 0 (reference-beats-description: "missing reference ⇒ generate it as a precursor").

## Evidence

- /Users/za/Downloads/Wanderland-Packet-2026-07-11/05-scripts-and-logs/work-log_readable.md lines ~4700–4840.
- Images: 03-generated-images/doorpanel_regionmap_v*.png in the same packet.

## Related

- [[fixed-cut-composite-flexible-cut-art-derived]]
- [[playwright-cdp-real-chrome-chatgpt-web-gen]]
- [[onepass-geometry-style-route-flux-control-lora]]

## Reproductions

- 2026-07-12, marine bedwrapper reef (this repo, live): map built by skills/region-map-guide, generated via subgen --provider openai (codex/gpt-image) — both candidates zone-adherent, left-right height delta +728/+905pt as specified, user accepted v1. Closes the OpenAI-provider question and shows the pattern transfers from architectural (door facade) to organic (coral reef) content. Fixture: skills/region-map-guide/examples/marine-reef.manifest.json.
- 2026-07-12, SAME reef map, provider probe: `subgen --provider nano` (Gemini/Nano Banana) — REJECTED on two axes. (1) GEOMETRY: nano treated the map+legend as loose inspiration — painted a full-frame reef, put the tallest element (seaweed) dead CENTER (map placed it left/orange), filled the black-dot keep-clear band where the turtle+star cutouts live, and did NOT lock the map aspect (output 1376x768 = 1.792 vs map 1.500). Overlay (nano vs map) shows art through the whole top ~60% keep-clear zone. (2) STYLE: output did NOT match the reference image's style (user verdict, 2026-07-12) — nano may simply be unable to reproduce that specific watercolor style. openai adhered on both axes on the same inputs. One run, but corroborates the prior banked pattern (openai > nano on hole/geom discipline; nano too loose). Conclusion: region maps need an aspect-locking, style-AND-geometry-disciplined provider — use openai/gpt-image, not nano.

## Open Questions

- (none outstanding) — nano tested 2026-07-12 and rejected on geometry AND style-match (see Reproductions); openai/gpt-image is the supported provider for region maps.
