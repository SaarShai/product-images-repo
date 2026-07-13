#!/usr/bin/env python3
"""Round-3: rich-style + thick-outline native-alpha gens.

User round-1 verdict (2026-07-13): O1/O2 edges "perfect", style too simple.
Direction: keep thicker non-anti-aliased outline character, raise style
detail/quality. gpt-image-2 rejects background=transparent (canary), so the
quality ladder is gpt-image-1 -> gpt-image-1.5 -> chatgpt-image-latest
(image-2 family), all via /v1/images/generations background=transparent.
"""
from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROUND_DIR = Path(__file__).resolve().parent
RAW_DIR = ROUND_DIR / "raws"
PROMPT_DIR = ROUND_DIR / "prompts"
MANIFEST_PATH = ROUND_DIR / "MANIFEST.json"

sys.path.insert(0, str(REPO / "scripts"))
from _falcommon import load_openai_key  # noqa: E402

SIZE = "1024x1536"
QUALITY = "high"
ENDPOINT = "https://api.openai.com/v1/images/generations"

MODELS = {
    "O1": "gpt-image-1",
    "O15": "gpt-image-1.5",
    "O2": "chatgpt-image-latest",
}

SUBJECT_BLOCK = (
    "[SUBJECT H]\n"
    "Create a single watercolor coral cluster with closed ink contours. "
    "The cluster must contain ALL of these visible elements: one legitimate "
    "green seaweed sprig, pale tinted off-white barnacle details, several "
    "deliberately thin fronds or antennae, and intentional negative-space "
    "gaps between branches. Nothing touches the canvas edges; keep a clear "
    "margin on all four sides."
)

RICH_STYLE_BLOCK = (
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

THICK_CONTOUR_BLOCK = (
    "[EDGE CONTOUR - THICK]\n"
    "Every painted shape is enclosed by a BOLD, continuous, fully closed ink "
    "contour with no gaps or fade-outs - a confident heavy outline roughly "
    "three times a pencil-line width, like a thick dip-pen or brush-ink "
    "outline in classic storybook art. The contour color is a clearly darker, "
    "more saturated version of the adjacent local fill - never pure black and "
    "never white. The outermost silhouette outline is the boldest line in the "
    "image. Every white-looking subject detail or highlight is a visibly "
    "tinted pastel off-white, fully enclosed by its contour."
)

KEYABLE_BLOCK = (
    "[KEYABLE-FINE]\n"
    "Fine detail is essential and must remain keyable: all thin fronds and "
    "antennae use full pigment strength, non-white mid-tones; every thinnest "
    "element has a closed contour; the minimum stroke is about a thick pencil "
    "line relative to the canvas; filaments are grouped into connected fans "
    "sharing one silhouette; no isolated strands over open background.\n"
    "Keyability overrides naturalism for thin features only: thin fronds and "
    "antennae may be slightly sturdier, rounder, and grouped while keeping "
    "their intended color, position, and role."
)

EXCLUSIONS_BLOCK = (
    "[EXCLUSIONS]\n"
    "No text, border, cut line, sticker rim, checkerboard, "
    "transparency-preview pattern, extra objects, or ground shadow."
)

ANTI_AURA_BLOCK = (
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

HARD_EDGE_BLOCK = (
    "[FACTUAL HARD EDGE]\n"
    "the outer silhouette boundary is a crisp hard step; nothing feathers, "
    "fades, or blends outside the contour; no semi-transparent outer "
    "transition band; no anti-aliasing at the outermost edge; transparency "
    "meets art color abruptly"
)


def build_prompt(level: str) -> str:
    parts = [
        SUBJECT_BLOCK,
        "",
        RICH_STYLE_BLOCK,
        "",
        THICK_CONTOUR_BLOCK,
        "",
        KEYABLE_BLOCK,
        "",
        EXCLUSIONS_BLOCK,
        "",
        ANTI_AURA_BLOCK,
    ]
    if level == "HARD":
        parts.extend(["", HARD_EDGE_BLOCK])
    return "\n".join(parts)


def alpha_ok(path: Path) -> bool:
    from PIL import Image

    with Image.open(path) as img:
        if "A" not in img.getbands():
            return False
        hist = img.getchannel("A").histogram()
        total = sum(hist)
        nonzero_bins = [i for i, c in enumerate(hist) if c]
        return (
            nonzero_bins
            and nonzero_bins[0] == 0
            and nonzero_bins[-1] == 255
            and len(nonzero_bins) > 2
            and hist[0] / total > 0.05
        )


def main() -> int:
    import requests

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROMPT_DIR.mkdir(parents=True, exist_ok=True)
    key = load_openai_key()
    manifest = {"experiment": "round3_rich", "size": SIZE, "quality": QUALITY, "entries": []}

    for level in ("AA", "HARD"):
        prompt = build_prompt(level)
        (PROMPT_DIR / f"rich_{level}.txt").write_text(prompt + "\n")
        for rid, model in MODELS.items():
            cell = f"H-{rid}-RICH-{level}"
            out = RAW_DIR / f"{cell}.png"
            entry = {"id": cell, "model": model, "level": level, "status": "pending"}
            if out.exists():
                entry["status"] = "skipped_existing"
                manifest["entries"].append(entry)
                print(f"SKIP {cell}")
                continue
            t0 = time.time()
            try:
                resp = requests.post(
                    ENDPOINT,
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": model,
                        "prompt": prompt,
                        "n": 1,
                        "size": SIZE,
                        "quality": QUALITY,
                        "background": "transparent",
                    },
                    timeout=240,
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                b64 = resp.json()["data"][0]["b64_json"]
                out.write_bytes(base64.b64decode(b64))
                entry["wall_secs"] = round(time.time() - t0, 1)
                entry["alpha_ok"] = alpha_ok(out)
                entry["status"] = "ok" if entry["alpha_ok"] else "alpha_failed"
                print(f"{entry['status'].upper():4s} {cell} ({entry['wall_secs']}s)")
            except Exception as exc:  # noqa: BLE001
                entry["status"] = "error"
                entry["error"] = str(exc)
                print(f"ERR  {cell}: {exc}", file=sys.stderr)
            manifest["entries"].append(entry)
            MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
