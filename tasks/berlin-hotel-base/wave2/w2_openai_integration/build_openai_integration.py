#!/usr/bin/env python3
"""Focused integration experiments for the preferred OpenAI building plate."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path("tasks/berlin-hotel-base")
OUTDIR = ROOT / "wave2/w2_openai_integration"
SRC = ROOT / "work/src.png"
DONOR = ROOT / "work/building_recreate/cand_openai_p1.png"
BOX = (3162, 2582, 4082, 2845)
ZOOM = (3050, 2480, 4120, 2900)
W = BOX[2] - BOX[0]
H = BOX[3] - BOX[1]


def color_match(patch: Image.Image) -> Image.Image:
    src = Image.open(SRC).convert("RGB")
    target = np.asarray(src.crop((3162, 2350, 4082, 2582))).astype(np.float32)
    arr = np.asarray(patch.convert("RGB")).astype(np.float32)
    tm, ts = target.reshape(-1, 3).mean(0), target.reshape(-1, 3).std(0)
    am, astd = arr.reshape(-1, 3).mean(0), arr.reshape(-1, 3).std(0)
    arr = (arr - am) / np.maximum(astd, 1) * np.maximum(ts * 0.86, 1) + tm
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


def source_carrier() -> Image.Image:
    src = Image.open(SRC).convert("RGB")
    # Larger source crop keeps upper rhythm and right-side perspective.
    carrier = src.crop((3162, 2318, 4082, 2581)).resize((W, H), Image.Resampling.BICUBIC)
    carrier = ImageEnhance.Contrast(carrier).enhance(0.82)
    carrier = ImageEnhance.Color(carrier).enhance(0.78)
    draw = ImageDraw.Draw(carrier, "RGBA")
    # Ground it without making a separate glass lobby.
    draw.rectangle((0, H - 38, W, H), fill=(177, 168, 145, 92))
    draw.line((0, H - 40, W, H - 40), fill=(92, 92, 84, 78), width=2)
    for y in range(H - 32, H, 11):
        draw.line((0, y, W, y), fill=(99, 97, 86, 55), width=1)
    return carrier.filter(ImageFilter.GaussianBlur(0.25))


def donor_patch(crop: tuple[int, int, int, int], width_scale: float = 1.0) -> Image.Image:
    donor = Image.open(DONOR).convert("RGB").crop(crop)
    target_w = max(1, int(W * width_scale))
    donor = donor.resize((target_w, H), Image.Resampling.LANCZOS)
    donor = color_match(donor)
    donor = ImageEnhance.Color(donor).enhance(0.66)
    donor = ImageEnhance.Contrast(donor).enhance(0.9)
    if target_w == W:
        return donor
    canvas = Image.new("RGB", (W, H), (226, 218, 194))
    x = (W - target_w) // 2
    canvas.paste(donor, (x, 0))
    return canvas


def detail_alpha(donor: Image.Image, strength: float = 1.0, top_hold: int = 0, right_fade_start: int | None = None) -> Image.Image:
    arr = np.asarray(donor.convert("RGB")).astype(np.int16)
    # Darker windows, piers, and ink lines carry useful architectural detail.
    darkness = np.maximum(0, 218 - arr.mean(axis=2))
    chroma = arr.std(axis=2)
    alpha = np.clip((darkness * 1.55 + chroma * 0.55) * strength, 0, 180)
    if top_hold:
        ramp = np.linspace(0, 1, max(top_hold, 1))[:, None]
        alpha[:top_hold, :] *= ramp
    if right_fade_start is not None:
        for x in range(right_fade_start, W):
            fade = max(0.0, 1.0 - (x - right_fade_start) / max(1, W - right_fade_start))
            alpha[:, x] *= fade
    alpha = Image.fromarray(alpha.astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2.0))
    return alpha


def foreground_mask(src_box: Image.Image) -> Image.Image:
    arr = np.asarray(src_box.convert("RGB"))
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    tree = (r > 120) & (g > 105) & (b < 105) & (np.indices(r.shape)[1] < 150)
    dark_rail = (arr.mean(axis=2) < 85) & (np.indices(r.shape)[0] > H - 90)
    mask = np.where(tree | dark_rail, 210, 0).astype(np.uint8)
    return Image.fromarray(mask, "L").filter(ImageFilter.GaussianBlur(1.2))


def edge_blend(src_box: Image.Image, patch: Image.Image) -> Image.Image:
    alpha = Image.new("L", (W, H), 255)
    px = alpha.load()
    for y in range(H):
        for x in range(W):
            a = 255
            if y < 24:
                a = min(a, int(255 * y / 24))
            if H - 1 - y < 14:
                a = min(a, int(255 * (H - 1 - y) / 14))
            if x < 6:
                a = min(a, int(255 * x / 6))
            if W - 1 - x < 6:
                a = min(a, int(255 * (W - 1 - x) / 6))
            px[x, y] = a
    return Image.composite(patch, src_box, alpha)


def save(name: str, patch: Image.Image, notes: str) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC).convert("RGB")
    src_box = src.crop(BOX)
    patch = Image.composite(src_box, patch, foreground_mask(src_box))
    patch = edge_blend(src_box, patch)
    out = src.copy()
    out.paste(patch, BOX[:2])
    out.save(OUTDIR / f"{name}.png")
    out.crop(ZOOM).save(OUTDIR / f"{name}_zoom.png")
    (OUTDIR / "method_notes.md").write_text(notes + "\n", encoding="utf-8")


def compose_detail(name: str, crop: tuple[int, int, int, int], width_scale: float, strength: float, top_hold: int, right_fade: int | None, notes: str) -> None:
    carrier = source_carrier()
    donor = donor_patch(crop, width_scale=width_scale)
    alpha = detail_alpha(donor, strength=strength, top_hold=top_hold, right_fade_start=right_fade)
    patch = Image.composite(donor, carrier, alpha)
    save(name, patch, notes)


def main() -> int:
    compose_detail(
        "openai_p1_detail_transfer_soft",
        (90, 1320, 900, 1578),
        1.0,
        0.82,
        92,
        760,
        "# w2_openai_integration\n\nSoft detail-transfer: OpenAI p1 lower base supplies dark windows/stone detail only; artwork facade is the carrier. Top seam and far-right face are faded back to source.",
    )
    compose_detail(
        "openai_p1_centered_front_face",
        (92, 1300, 870, 1580),
        0.82,
        1.1,
        84,
        700,
        "# w2_openai_integration\n\nCentered front-face registration: narrower OpenAI donor centered on the main face, leaving right-side perspective and margins source-led.",
    )
    compose_detail(
        "openai_p1_groundfloor_only",
        (88, 1395, 902, 1586),
        0.9,
        1.25,
        48,
        720,
        "# w2_openai_integration\n\nGround-floor-only donor: uses only the lower OpenAI plate so the seam is mostly source rhythm; tests whether base detail can be inserted without a full podium slab.",
    )
    compose_detail(
        "openai_p1_floor_rhythm_crop",
        (86, 1170, 902, 1578),
        0.96,
        0.72,
        128,
        760,
        "# w2_openai_integration\n\nFloor-rhythm crop: larger OpenAI vertical crop downscaled into the box so floor spacing is less compressed; donor detail fades in below the seam.",
    )
    print(f"wrote integration candidates to {OUTDIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

