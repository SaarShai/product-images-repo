#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
TASK = ROOT / "tasks/berlin-hotel-base/wave13_regenerate_bridge_crop"
TEMPLATE_FILE = TASK / "prompts/templates_round1.md"
OUT_DIR = TASK / "prompts/round1"


COMMON_SCENE = """\
Scene facts to preserve:
- Same rectangular bridge crop, no border, no labels, no text.
- Horizontal warm brick bridge deck across the middle.
- Large central red-brick arch with bright pale water visible through it.
- Yellow train remains cropped on the left elevated track.
- Left and right gray block-stone bridge piers descend into the water and support the bridge deck.
- Each pier has a small orange-brown turret roof and warm brick turret body.
- Circular medallions stay on the bridge face.
- Background stays soft: pale stone stairs, leafy trees, and historic architecture.
- Water remains blue-gray with cream watercolor ripples and reflections.
- Keep the hand-painted watercolor and ink style, not photorealism, 3D, vector art, or a new design.
"""

OPENAI_PREFIX = """\
Edit the first attached image in place. It is the base canvas and composition authority.
The second attached image is only a reference for the existing pier/turret character.
Preserve exact framing, scale, perspective, object positions, aspect ratio, and crop boundaries.
Continuity cleanup only: recreate the same scene as a coherent finished watercolor illustration, not a new bridge design or recomposition.
"""

NANO_PREFIX = """\
Use the first attached image as the exact base canvas. Return the same rectangular crop.
No zoom, pan, recentering, crop expansion, border, or new composition.
The second attached image is a reference only for the bridge pier/turret character.
Match the existing loose watercolor-and-ink softness; do not make it digital, sharp, photorealistic, or square.
"""


def load_templates() -> list[tuple[int, str]]:
    text = TEMPLATE_FILE.read_text()
    matches = re.findall(r"(?ms)^(\d+)\.\s+(.*?)(?=^\d+\.|\Z)", text)
    return [(int(n), " ".join(body.strip().split())) for n, body in matches]


def write_prompt(provider: str, idx: int, body: str) -> None:
    prefix = OPENAI_PREFIX if provider == "openai" else NANO_PREFIX
    prompt = f"""{prefix}

Template {idx}:
{body}

{COMMON_SCENE}

Output: exactly one regenerated image of the same crop.
"""
    path = OUT_DIR / provider / f"r1_t{idx:02d}_{provider}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt)


def main() -> int:
    templates = load_templates()
    if len(templates) != 20:
        raise SystemExit(f"expected 20 templates, found {len(templates)}")
    for idx, body in templates:
        write_prompt("openai", idx, body)
        write_prompt("nano", idx, body)
    print(f"wrote {len(templates) * 2} prompt files under {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
