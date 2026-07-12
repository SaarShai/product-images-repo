#!/usr/bin/env python3
"""Build source-vs-candidate native-resolution crops for visual diagnosis only."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
OUT = Path(__file__).resolve().parent / "diagnostics"

CASES = {
    "image15": {
        "source": PRODUCT / "ChatGPT Image Jul 7, 2026, 11_34_15 AM.png",
        "candidate": PRODUCT
        / "Images/candidates/bg-assisted-v2/image15/auto-proposal-v1/"
        "image15-auto-v1-rgba.png",
        "crops": {
            "bottom-left": (0, 680, 560, 1024),
            "bottom-center": (480, 680, 1080, 1024),
            "bottom-right": (1000, 680, 1536, 1024),
            "upper-left-holes": (0, 120, 540, 690),
            "upper-center-holes": (500, 90, 1080, 690),
            "upper-right-holes": (1010, 90, 1536, 700),
            "mid-left-gaps": (0, 400, 540, 820),
            "mid-center-gaps": (500, 400, 1080, 820),
            "mid-right-gaps": (1000, 400, 1536, 820),
            "far-right-paper": (1420, 480, 1536, 800),
        },
    },
    "sample08": {
        "source": PRODUCT / "ChatGPT Image Jul 7, 2026, 11_09_25 AM.png",
        "candidate": PRODUCT
        / "Images/candidates/bg-assisted-v2/sample08/auto-proposal-v1/"
        "sample08-auto-v1-rgba.png",
        "crops": {
            "bottom-left": (0, 610, 620, 962),
            "bottom-center": (500, 610, 1130, 962),
            "bottom-right": (1030, 610, 1634, 962),
            "upper-left-holes": (0, 150, 650, 740),
            "upper-center-holes": (520, 0, 1150, 750),
            "upper-right-holes": (1040, 150, 1634, 750),
            "mid-left-gaps": (0, 420, 620, 820),
            "mid-center-gaps": (500, 420, 1130, 820),
            "mid-right-gaps": (1030, 420, 1634, 820),
            "far-right-paper": (1460, 500, 1634, 830),
            "far-left-paper": (0, 380, 180, 830),
            "bubble-a": (390, 320, 470, 400),
            "bubble-b": (900, 280, 970, 350),
            "bubble-c": (1050, 430, 1130, 510),
            "bubble-d": (1520, 540, 1600, 640),
        },
    },
}


def composite(candidate: Image.Image, color: tuple[int, int, int, int]) -> Image.Image:
    background = Image.new("RGBA", candidate.size, color)
    return Image.alpha_composite(background, candidate).convert("RGB")


def labeled_pair(left: Image.Image, right: Image.Image) -> Image.Image:
    header = 24
    board = Image.new("RGB", (left.width + right.width, left.height + header), "white")
    board.paste(left, (0, header))
    board.paste(right, (left.width, header))
    draw = ImageDraw.Draw(board)
    draw.text((6, 6), "SOURCE", fill="black")
    draw.text((left.width + 6, 6), "CANDIDATE ON MAGENTA", fill="black")
    return board


def paper_contrast(
    source: Image.Image, alpha: Image.Image, *, show_removed: bool
) -> Image.Image:
    """Normalize paper to gray and show either removed or retained source pixels."""
    source_array = np.asarray(source, dtype=np.int16)
    alpha_array = np.asarray(alpha)
    corners = np.concatenate(
        [
            source_array[:32, :32].reshape(-1, 3),
            source_array[:32, -32:].reshape(-1, 3),
            source_array[-32:, :32].reshape(-1, 3),
            source_array[-32:, -32:].reshape(-1, 3),
        ]
    )
    paper = np.median(corners, axis=0)
    contrast = np.clip(128 + (source_array - paper) * 6, 0, 255).astype(np.uint8)
    if show_removed:
        contrast[alpha_array >= 64] = 0
    else:
        contrast[alpha_array < 192] = 0
    return Image.fromarray(contrast)


def main() -> None:
    for case, spec in CASES.items():
        source = Image.open(spec["source"]).convert("RGB")
        candidate = Image.open(spec["candidate"]).convert("RGBA")
        if source.size != candidate.size:
            raise ValueError(f"{case}: source {source.size} != candidate {candidate.size}")
        magenta = composite(candidate, (255, 0, 255, 255))
        alpha = candidate.getchannel("A")
        removed = paper_contrast(source, alpha, show_removed=True)
        retained = paper_contrast(source, alpha, show_removed=False)
        case_out = OUT / case
        case_out.mkdir(parents=True, exist_ok=True)
        for name, box in spec["crops"].items():
            source_crop = source.crop(box)
            magenta_crop = magenta.crop(box)
            alpha_crop = alpha.crop(box)
            removed_crop = removed.crop(box)
            retained_crop = retained.crop(box)
            labeled_pair(source_crop, magenta_crop).save(case_out / f"{name}-compare.png")
            alpha_crop.save(case_out / f"{name}-alpha.png")
            removed_crop.save(case_out / f"{name}-removed-contrast.png")
            retained_crop.save(case_out / f"{name}-retained-contrast.png")


if __name__ == "__main__":
    main()
