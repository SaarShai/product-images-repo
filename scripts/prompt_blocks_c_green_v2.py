#!/usr/bin/env python3
"""prompt_blocks_c_green_v2.py — FROZEN prompt blocks for Route C-green v2.

Canonical, user-validated (2026-07-13, round 7, "best yet — bank it") prompt
recipe for `gpt-image-2` chroma-key generation. Every block below is copied
VERBATIM from the round-3/4/6/7 generation scripts
(`tasks/transparent-bg-endgame/round{3,4,6,7}_*/gen_round*.py`) — do not
paraphrase or "improve" wording here; each block's exact phrasing was earned
by a user-feedback round (see PIPELINE.md / SKILL.md "ROUTE C-green v2").

This module is the single source of truth for the runner
(`scripts/run_c_green_v2.py`). If you need to change a block, change it in
BOTH this file and the round-7 source, or better: only touch this file and
update PIPELINE.md/SKILL.md's citation.

RICH_STYLE and the exclusion/anti-halo blocks (EXCLUSIONS, ANTI_AURA, KEY_BG,
HARD_EDGE) are CORAL-TUNED: their vocabulary (glazes, polyp dots, barnacle
rings, "seabed"/"sand" exclusions, etc.) was validated round-7 on a coral
subject only, not re-validated against other product classes. New product
classes MUST keep the mandatory geometry/safety blocks byte-identical
(SIGNIFICANT_CONTOUR_BLOCK, NO_FILAMENT_BLOCK, NO_GREEN_ART_BLOCK — contour,
no-filament, no-green-art are subject-independent structural requirements of
the chroma-key pipeline), but should review whether the coral-specific style
vocabulary in RICH_STYLE/the exclusion blocks still fits before trusting the
prompt untouched for a non-coral subject.
"""
from __future__ import annotations

import hashlib

# ---------------------------------------------------------------------------
# Blocks — verbatim from round3_rich/gen_round3.py
# ---------------------------------------------------------------------------

RICH_STYLE_ID = "RICH_STYLE"
RICH_STYLE = (
    "[STYLE]\n"
    "Highly detailed professional storybook watercolor-and-ink illustration, "
    "gallery quality: layered translucent glazes with rich pigment depth, "
    "visible granulation and wet-on-wet blooms INSIDE the shapes, subtle "
    "color-temperature shifts across each form, intricate fine ink work for "
    "interior texture (polyp dots, ridge hatching, barnacle rings, vein "
    "lines), a sophisticated harmonious palette with deep saturated accents "
    "as well as pastels, and confident hand-drawn line quality. Maximum "
    "interior detail and painterly richness; the complexity lives INSIDE the "
    "contours, never outside them."
)

EXCLUSIONS_ID = "EXCLUSIONS"
EXCLUSIONS = (
    "[EXCLUSIONS]\n"
    "No text, border, cut line, sticker rim, checkerboard, "
    "transparency-preview pattern, extra objects, or ground shadow."
)

HARD_EDGE_ID = "HARD_EDGE"
HARD_EDGE = (
    "[FACTUAL HARD EDGE]\n"
    "the outer silhouette boundary is a crisp hard step; nothing feathers, "
    "fades, or blends outside the contour; no semi-transparent outer "
    "transition band; no anti-aliasing at the outermost edge; transparency "
    "meets art color abruptly"
)

# ---------------------------------------------------------------------------
# Block — verbatim from round3_rich/gen_round3.py (ANTI_AURA_BLOCK)
# ---------------------------------------------------------------------------

ANTI_AURA_ID = "ANTI_AURA"
ANTI_AURA = (
    "[ANTI-AURA]\n"
    "isolated cutout on true transparency; transparent pixels begin "
    "immediately outside the outermost inked subject contour; all pigment and "
    "paper-grain texture remain inside the subject silhouette only; no "
    "surrounding watercolor wash, color bloom, glow, aura, halo, rim light, "
    "backlight, mist, vignette, drop shadow, ambient color spill, or diffuse "
    "silhouette expansion; flat ambient lighting; preserve rich watercolor "
    "texture inside the forms, but no pigment outside them; only a 1-2 pixel "
    "antialiased transition at the actual art edge.\n"
    "No sand, no seabed, no ground plane, no soil, no rock base, no surface "
    "for the subject to rest on, no cast shadow or contact shadow beneath the "
    "subject; the subject is a fully isolated floating cutout; transparency "
    "begins immediately below the lowest painted element.\n"
    "No backdrop, no background panel, no pale wash patch behind or between "
    "the subject elements; every painted area belongs to a named subject "
    "element; the gaps between branches and elements are fully transparent, "
    "never filled with pale paint."
)

# ---------------------------------------------------------------------------
# Block — verbatim from round4_key/gen_round4.py (key_bg_block)
# ---------------------------------------------------------------------------


def key_bg_block(desc: str) -> str:
    """Verbatim from round4_key/gen_round4.py::key_bg_block()."""
    return (
        "[BACKGROUND - FLAT KEY]\n"
        f"The entire background is a single perfectly flat, uniform field of "
        f"{desc} - one exact solid color across every background pixel. "
        "Absolutely no gradient, vignette, texture, paper grain, noise, "
        "lighting variation, or shadow anywhere in the background. The "
        "background color must never appear inside the subject: no colored "
        "reflections, color spill, rim light, or ambient tint from the "
        "background onto the artwork. The subject's outermost bold ink "
        "contour meets the flat background color abruptly, with no glow, "
        "halo, aura, wash, bloom, mist, drop shadow, contact shadow, ground "
        "plane, or soft transition band around the silhouette. No sand, "
        "seabed, rock base, or any surface; the subject floats on the flat "
        "color field. Gaps between branches show only the flat background "
        "color, never pale paint."
    )


KEY_BG_ID = "KEY_BG"
GREEN_HEX = "#00FF00"
GREEN_DESC = "pure bright chroma green (#00FF00)"

# ---------------------------------------------------------------------------
# Blocks — verbatim from round6_clean/gen_round6.py
# ---------------------------------------------------------------------------

NO_FILAMENT_ID = "NO_FILAMENT"
NO_FILAMENT_BLOCK = (
    "[STRUCTURE - NO LOOSE FILAMENTS]\n"
    "Absolutely no feather-duster fans, hair-thin tentacle sprays, or "
    "clusters of individual wispy strands radiating over open background. "
    "Every branch, frond, and antenna is a SOLID painted shape at least as "
    "wide as a fine felt-tip line, with its own closed contour, and branch "
    "junctions merge smoothly into solid painted joints - no lattice of "
    "crossing hairlines with background showing through the crossings. "
    "Delicacy comes from interior brushwork and color, not from strand "
    "thinness."
)

NO_GREEN_ART_ID = "NO_GREEN_ART"
NO_GREEN_ART_BLOCK = (
    "[PALETTE CONSTRAINT - NO PURE GREEN]\n"
    "Because the background is pure chroma green, NO part of the subject may "
    "use bright, pure, or saturated green. Any plant or seaweed element uses "
    "muted olive, sage, sea-teal, or yellow-green earth tones clearly "
    "distinct from the background green. No green highlights, no green "
    "reflections, no grass-green accents anywhere in the artwork."
)

# ---------------------------------------------------------------------------
# Block — verbatim from round7_outline/gen_round7.py
# ---------------------------------------------------------------------------

SIGNIFICANT_CONTOUR_ID = "SIGNIFICANT_CONTOUR"
SIGNIFICANT_CONTOUR_BLOCK = (
    "[EDGE CONTOUR - SIGNIFICANT, MANDATORY]\n"
    "This is a NON-NEGOTIABLE style requirement: every shape in the artwork "
    "is enclosed by a clearly VISIBLE, continuous, fully closed dark ink "
    "contour line - like classic pen-and-ink illustration with watercolor "
    "fill. The line is slim and elegant (fine felt-tip weight, never chunky), "
    "but it must be DARK and OBVIOUS at a glance: a deep, saturated, darker "
    "shade of the adjacent fill color, never faded, never soft, never "
    "blended away. The outermost silhouette of the whole subject carries the "
    "most defined, unbroken line in the image; if any part of the silhouette "
    "lacks a visible dark contour line the image is wrong. No open, soft, or "
    "lineless watercolor edges anywhere."
)

# ---------------------------------------------------------------------------
# Mandatory-block set + assembler
# ---------------------------------------------------------------------------

# Block IDs that MUST be present for a Route C-green v2 prompt to be valid.
# (ANTI_AURA is round-3 evidence but is superseded/subsumed for the round-7
# recipe by SIGNIFICANT_CONTOUR + key_bg_block's own anti-halo language per
# PIPELINE.md "ROUTE C-green v2"; it is not required here.)
MANDATORY_BLOCK_IDS = (
    SIGNIFICANT_CONTOUR_ID,
    NO_FILAMENT_ID,
    NO_GREEN_ART_ID,
    KEY_BG_ID,
    HARD_EDGE_ID,
)

# ---------------------------------------------------------------------------
# Frozen sha256 registry — tamper check.
#
# Each hash below was computed ONCE from the verbatim-validated block text
# above and is now a frozen literal. assemble_prompt() recomputes the sha256
# of each live block at call time and asserts it matches; a mismatch means a
# block's text drifted from the validated round-3/4/6/7 recipe without this
# registry being updated, and the run must hard-fail rather than silently
# ship an unvalidated prompt. Do NOT "fix" a mismatch by editing the hash to
# match new text — that defeats the check. If a block is deliberately
# changed, re-validate it first, then update both the block text and its hash
# together in the same edit.
# ---------------------------------------------------------------------------
BLOCK_SHA256 = {
    RICH_STYLE_ID: "3b449cfcd9804c3a792799a49da190e5034dd10698e649bb52e51c120084fa88",
    SIGNIFICANT_CONTOUR_ID: "0eeba90bac8d1574000185768abb457e9e83c08ce4a4dfb851c2d1a391a83a2f",
    NO_FILAMENT_ID: "b1485cce88707d7923d8806abebaf85db6291c63b0148ee6f701d3960b3ad542",
    NO_GREEN_ART_ID: "76807ca7d1297f52d1fedf145527b158ab6192f963cf8593f411d83d39738398",
    EXCLUSIONS_ID: "6354902b8953d32ec323efc5710bac5e0e3699397b91711a3e7c5a504b37fd62",
    KEY_BG_ID: "35d5a880554269d50c4434d113fce17bff339735fb6d1730f23094a8750ae980",
    HARD_EDGE_ID: "f6729daaae1e67b9c1bccdbf7dc7f4da876c79260e59d5ab5c9305af9d45f95d",
    ANTI_AURA_ID: "1ff113d5f1c4c470c894f211d3a46971ac9dc3064a09a66462891386574c1609",
}


def assemble_prompt(subject: str) -> tuple[str, str]:
    """Assemble the validated Route C-green v2 prompt for `subject`.

    Mirrors round7_outline/gen_round7.py::build_prompt(), with SUBJECT_BLOCK_V2
    replaced by the caller-supplied `subject` text (round7's SUBJECT_BLOCK_V2
    was itself a fixed coral-cluster subject; this generalizes it to any
    product subject while keeping every OTHER block byte-identical to the
    validated recipe).

    Returns (prompt_text, sha256_hexdigest).
    Raises AssertionError if any mandatory block is missing from the assembly
    (guards against a future edit silently dropping a load-bearing block).
    """
    if not subject or not subject.strip():
        raise ValueError("subject must be non-empty")

    subject_block = f"[SUBJECT]\n{subject.strip()}"

    parts = [
        (None, subject_block),
        (RICH_STYLE_ID, RICH_STYLE),
        (SIGNIFICANT_CONTOUR_ID, SIGNIFICANT_CONTOUR_BLOCK),
        (NO_FILAMENT_ID, NO_FILAMENT_BLOCK),
        (NO_GREEN_ART_ID, NO_GREEN_ART_BLOCK),
        (EXCLUSIONS_ID, EXCLUSIONS),
        (KEY_BG_ID, key_bg_block(GREEN_DESC)),
        (HARD_EDGE_ID, HARD_EDGE),
    ]

    present_ids = {block_id for block_id, _ in parts if block_id}
    missing = [bid for bid in MANDATORY_BLOCK_IDS if bid not in present_ids]
    assert not missing, f"assemble_prompt: missing mandatory block(s): {missing}"

    # Tamper check: recompute each registered block's sha256 at call time and
    # compare against the frozen BLOCK_SHA256 registry. A mismatch means the
    # block text has drifted from the verbatim-validated recipe.
    tampered = [
        block_id
        for block_id, text in parts
        if block_id in BLOCK_SHA256
        and hashlib.sha256(text.encode("utf-8")).hexdigest() != BLOCK_SHA256[block_id]
    ]
    assert not tampered, (
        f"assemble_prompt: block text no longer matches frozen BLOCK_SHA256 "
        f"registry, block(s): {tampered} — see BLOCK_SHA256 comment"
    )

    prompt = "\n\n".join(text for _, text in parts)
    sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return prompt, sha256


if __name__ == "__main__":
    p, h = assemble_prompt("a single watercolor autumn maple leaf, closed ink contours")
    print(f"sha256={h}")
    print(f"len={len(p)} chars")
    print(p)
