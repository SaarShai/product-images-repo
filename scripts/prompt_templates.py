#!/usr/bin/env python3
"""prompt_templates.py — reusable edit prompts encoding the verified best-practices
(research dossier E: BFL/FLUX.2/OpenAI guidance). Stops re-deriving prompts and bakes in the
fixes for our failure modes: REFRAME/zoom, added TEXT, realism DRIFT, instance INCONSISTENCY.

Key rules baked in:
- name the subject, use scoped verbs (replace/redraw, never "transform").
- anti-reframe clause (keep position/scale/pose; do not zoom/recenter/reframe/crop).
- POSITIVE no-text phrasing (surfaces blank, add no text) — negatives are unreliable; FLUX.2 has none.
- PRESCRIBE the medium ("flat 2D storybook watercolor and ink, no photo/3D shading"), don't say "keep the style".

CLI: python3 scripts/prompt_templates.py redraw --element "the yellow taxi" --desc "a clean classic NYC sedan" --medium "loose watercolor and ink children's-book"
"""
import argparse

MEDIUM = "loose hand-drawn watercolor and ink children's-book illustration, soft outlines, visible paper texture, flat 2D — no photographic shading, no 3D render, no gloss"
ANTI_REFRAME = ("Keep everything else exactly the same: identical composition, same camera angle, framing, crop, "
                "perspective; same position, scale and proportions; same colors and lighting. "
                "Do not zoom, recenter, reframe or crop.")
NO_TEXT = "Keep all surfaces and signage blank — add no text, letters, words, numbers, logos or watermarks."


def redraw(element, desc, medium=MEDIUM, **_):
    return (f"Replace only {element} with {desc}. Render it in the EXACT same {medium}. "
            f"{ANTI_REFRAME} {NO_TEXT}")


def restyle_fit(element, desc, medium=MEDIUM, **_):
    return (f"Redraw {element} as {desc}, fitting the same outline/footprint. Match the surrounding {medium}, "
            f"its textured brush strokes and palette. {ANTI_REFRAME} {NO_TEXT}")


def consistency(element, desc, medium=MEDIUM, **_):
    return (f"Redraw {element} to MATCH the approved reference (image 2): same design, proportions, colors and "
            f"{medium}, adapted to its current pose. Render a COMPLETE figure — no part fades or trails off. "
            f"{ANTI_REFRAME} {NO_TEXT}")


def plain_sedan(**_):
    return (f"A plain {MEDIUM} yellow taxi car, side view: correct car body, two round wheels, clear windows, "
            f"smooth roof with nothing on top. {NO_TEXT}")


TEMPLATES = {"redraw": redraw, "restyle_fit": restyle_fit, "consistency": consistency, "plain_sedan": plain_sedan}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template", choices=list(TEMPLATES))
    ap.add_argument("--element", default="the element")
    ap.add_argument("--desc", default="a clean version")
    ap.add_argument("--medium", default=MEDIUM)
    a = ap.parse_args()
    print(TEMPLATES[a.template](element=a.element, desc=a.desc, medium=a.medium))


if __name__ == "__main__":
    main()
