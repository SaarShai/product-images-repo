#!/usr/bin/env python3
"""Create native-size source/candidate ROIs for exhaustive branch-gap review."""

from pathlib import Path

from PIL import Image, ImageDraw


PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
OUT = Path(__file__).resolve().parent / "diagnostics" / "loop-audit"

CASES = {
    "image15": {
        "source": PRODUCT / "ChatGPT Image Jul 7, 2026, 11_34_15 AM.png",
        "candidate": PRODUCT
        / "Images/candidates/bg-assisted-v2/image15/auto-proposal-v1/"
        "image15-auto-v1-rgba.png",
        "rois": {
            "I01-left-peach-coral": (0, 210, 235, 660),
            "I02-left-kelp-curl": (175, 90, 420, 520),
            "I03-left-lower-pink-coral": (140, 380, 430, 770),
            "I04-mid-pink-coral": (410, 360, 770, 760),
            "I05-center-kelp": (735, 90, 1090, 720),
            "I06-right-lavender-coral": (1000, 250, 1320, 690),
            "I07-right-large-pink-coral": (1130, 90, 1536, 680),
            "I08-right-orange-coral": (900, 460, 1280, 850),
            "I09-left-lower-blue-branches": (0, 500, 245, 840),
            "I10-right-lower-blue-branches": (1250, 480, 1536, 830),
        },
    },
    "sample08": {
        "source": PRODUCT / "ChatGPT Image Jul 7, 2026, 11_09_25 AM.png",
        "candidate": PRODUCT
        / "Images/candidates/bg-assisted-v2/sample08/auto-proposal-v1/"
        "sample08-auto-v1-rgba.png",
        "rois": {
            "S01-left-tall-orange-coral": (70, 200, 490, 710),
            "S02-left-blue-green-branches": (0, 400, 300, 800),
            "S03-left-lower-orange-coral": (160, 480, 560, 850),
            "S04-mid-purple-coral": (280, 360, 730, 740),
            "S05-center-kelp": (550, 20, 960, 730),
            "S06-center-right-kelp": (840, 190, 1210, 730),
            "S07-right-large-coral": (1100, 170, 1610, 670),
            "S08-right-lower-orange-coral": (920, 480, 1340, 820),
            "S09-right-green-sprig": (1350, 450, 1634, 800),
        },
    },
}


def compare(source: Image.Image, candidate: Image.Image, box: tuple[int, ...]) -> Image.Image:
    source_crop = source.crop(box)
    candidate_crop = candidate.crop(box)
    magenta = Image.new("RGBA", candidate_crop.size, (255, 0, 255, 255))
    candidate_magenta = Image.alpha_composite(magenta, candidate_crop).convert("RGB")
    header = 24
    board = Image.new("RGB", (source_crop.width * 2, source_crop.height + header), "white")
    board.paste(source_crop, (0, header))
    board.paste(candidate_magenta, (source_crop.width, header))
    draw = ImageDraw.Draw(board)
    draw.text((6, 6), "SOURCE", fill="black")
    draw.text((source_crop.width + 6, 6), "CANDIDATE ON MAGENTA", fill="black")
    return board


def main() -> None:
    for case, spec in CASES.items():
        source = Image.open(spec["source"]).convert("RGB")
        candidate = Image.open(spec["candidate"]).convert("RGBA")
        if source.size != candidate.size:
            raise ValueError(f"{case}: source {source.size} != candidate {candidate.size}")
        case_out = OUT / case
        case_out.mkdir(parents=True, exist_ok=True)
        for roi, box in spec["rois"].items():
            compare(source, candidate, box).save(case_out / f"{roi}.png")


if __name__ == "__main__":
    main()
