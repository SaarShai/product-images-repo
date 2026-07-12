#!/usr/bin/env python3
"""Render sparse, manually diagnosed foreground/background correction strokes."""

from pathlib import Path

from PIL import Image, ImageDraw


PRODUCT = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/"
    "double Marine Bed Wrapper/images"
)
HERE = Path(__file__).resolve().parent

RED = (255, 0, 0, 255)
BLUE = (0, 0, 255, 255)

CASES = {
    "image15": {
        "source": PRODUCT / "ChatGPT Image Jul 7, 2026, 11_34_15 AM.png",
        "candidate": PRODUCT
        / "Images/candidates/bg-assisted-v2/image15/auto-proposal-v1/"
        "image15-auto-v1-rgba.png",
        "output": PRODUCT
        / "Images/candidates/bg-assisted-v2/image15/corrections-v1/"
        "image15-corrections-v1-rgba.png",
        # Clear false-negative foreground: authored sand/watercolor wash visibly
        # continues below the automatic cut. Paths stay inside colored/marked wash.
        "red_paths": [
            [(25, 875), (70, 882), (110, 890)],
            [(105, 925), (135, 932), (165, 938)],
            [(195, 930), (230, 934), (270, 930)],
            [(275, 934), (315, 938), (350, 938)],
            [(440, 920), (520, 930), (590, 935)],
            [(565, 935), (650, 945), (735, 948)],
            [(720, 946), (810, 952), (900, 946)],
            [(890, 945), (975, 938), (1055, 925)],
            [(1040, 925), (1127, 930), (1212, 920)],
            [(1193, 918), (1281, 920), (1363, 910)],
            [(1360, 915), (1420, 910), (1490, 900)],
        ],
        "red_circles": [],
        # No visually unambiguous false-positive paper survived in the reviewed
        # native crops. Ambiguous pale foam and watercolor rims remain unknown.
        "blue_paths": [],
        "blue_circles": [],
    },
    "sample08": {
        "source": PRODUCT / "ChatGPT Image Jul 7, 2026, 11_09_25 AM.png",
        "candidate": PRODUCT
        / "Images/candidates/bg-assisted-v2/sample08/auto-proposal-v1/"
        "sample08-auto-v1-rgba.png",
        "output": PRODUCT
        / "Images/candidates/bg-assisted-v2/sample08/corrections-v1/"
        "sample08-corrections-v1-rgba.png",
        "red_paths": [],
        # Clear false-negative foreground: small painted blue bubbles present in
        # the source but absent against all candidate review backgrounds.
        "red_circles": [
            (433, 346, 4),
            (931, 337, 3),
            (1120, 462, 3),
        ],
        # The reviewed branch/kelp gaps are already transparent. Do not turn
        # bubble interiors, pale rocks, or antialiased rims into invented BG.
        "blue_paths": [],
        "blue_circles": [],
    },
}


def draw_labels(spec: dict) -> Image.Image:
    source = Image.open(spec["source"])
    overlay = Image.new("RGBA", source.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for path in spec["red_paths"]:
        draw.line(path, fill=RED, width=5, joint="curve")
    for x, y, radius in spec["red_circles"]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=RED)
    for path in spec["blue_paths"]:
        draw.line(path, fill=BLUE, width=5, joint="curve")
    for x, y, radius in spec["blue_circles"]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=BLUE)
    return overlay


def preview(spec: dict, overlay: Image.Image) -> Image.Image:
    source = Image.open(spec["source"]).convert("RGBA")
    candidate = Image.open(spec["candidate"]).convert("RGBA")
    magenta = Image.new("RGBA", source.size, (255, 0, 255, 255))
    candidate_magenta = Image.alpha_composite(magenta, candidate)
    visible = overlay.copy()
    visible.putalpha(overlay.getchannel("A").point(lambda value: round(value * 0.82)))
    source_preview = Image.alpha_composite(source, visible).convert("RGB")
    candidate_preview = Image.alpha_composite(candidate_magenta, visible).convert("RGB")
    board = Image.new("RGB", (source.width * 2, source.height), "white")
    board.paste(source_preview, (0, 0))
    board.paste(candidate_preview, (source.width, 0))
    return board


def main() -> None:
    review_dir = HERE / "diagnostics" / "correction-previews"
    review_dir.mkdir(parents=True, exist_ok=True)
    for case, spec in CASES.items():
        overlay = draw_labels(spec)
        spec["output"].parent.mkdir(parents=True, exist_ok=True)
        overlay.save(spec["output"])
        preview(spec, overlay).save(review_dir / f"{case}-source-candidate-preview.png")


if __name__ == "__main__":
    main()
