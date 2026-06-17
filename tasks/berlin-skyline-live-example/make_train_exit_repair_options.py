#!/usr/bin/env python3
"""Create local train-exit repair options for Berlin Image A.

The edit is intentionally local and artwork-only: no template guide geometry is
drawn into the artwork. Existing overlay tooling is reused afterward for review.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


TASK = Path("tasks/berlin-skyline-live-example")
BASE = TASK / "refs/user-feedback/20260616-image-a-artwork-only.png"
OUT = TASK / "outputs/reviews/train-exit-repair"


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


TITLE = font(28, True)
BODY = font(18)


def soft_paste(base: Image.Image, layer: Image.Image, blur: float = 0.7) -> Image.Image:
    alpha = layer.getchannel("A").filter(ImageFilter.GaussianBlur(blur))
    layer = layer.copy()
    layer.putalpha(alpha)
    out = base.copy()
    out.alpha_composite(layer)
    return out


def draw_waterline(draw: ImageDraw.ImageDraw, x0: int, y: int, x1: int, color: tuple[int, int, int, int]) -> None:
    for i, off in enumerate((0, 8, 17, 27)):
        draw.arc((x0 + off, y - 8, x0 + 78 + off, y + 10), 190, 345, fill=color, width=2 if i < 2 else 1)


def option_tunnel(base: Image.Image) -> Image.Image:
    img = base.copy().convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")

    # Local repair area: train terminus just before the central masonry tower.
    arch_box = (410, 622, 535, 790)
    d.rounded_rectangle((398, 650, 543, 812), radius=8, fill=(180, 158, 118, 100))
    d.arc(arch_box, 180, 360, fill=(91, 79, 64, 185), width=16)
    d.line((410, 706, 410, 806), fill=(91, 79, 64, 175), width=12)
    d.line((535, 706, 535, 806), fill=(91, 79, 64, 175), width=12)
    d.rectangle((420, 707, 526, 808), fill=(48, 56, 58, 150))
    d.arc((422, 650, 524, 760), 180, 360, fill=(30, 38, 42, 190), width=34)
    d.rectangle((439, 704, 508, 790), fill=(27, 34, 37, 180))

    # Stone blocks and watercolor texture.
    for x in (404, 430, 458, 488, 518):
        d.line((x, 718, x, 805), fill=(107, 96, 78, 90), width=2)
    for y in (734, 758, 783):
        d.line((402, y, 540, y + 2), fill=(107, 96, 78, 80), width=2)
    d.line((405, 811, 543, 802), fill=(88, 78, 66, 140), width=5)
    draw_waterline(d, 406, 823, 535, (83, 112, 118, 120))

    return soft_paste(img, layer)


def option_tunnel_refined(base: Image.Image) -> Image.Image:
    img = base.copy().convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")

    # Smaller portal that reads as an exit without becoming the visual hero.
    d.rounded_rectangle((420, 666, 523, 804), radius=7, fill=(179, 154, 113, 55))
    d.arc((418, 642, 525, 774), 180, 360, fill=(96, 82, 63, 130), width=10)
    d.line((420, 704, 420, 804), fill=(96, 82, 63, 115), width=8)
    d.line((523, 704, 523, 804), fill=(96, 82, 63, 115), width=8)
    d.arc((431, 664, 512, 773), 180, 360, fill=(42, 50, 51, 145), width=24)
    d.rectangle((443, 718, 500, 800), fill=(35, 43, 45, 118))

    # Continue rails into the dark mouth so the train has a path.
    d.line((355, 781, 455, 765), fill=(48, 55, 54, 115), width=3)
    d.line((358, 795, 462, 783), fill=(48, 55, 54, 105), width=3)
    for x in (432, 454, 478, 501):
        d.line((x, 720, x, 803), fill=(108, 91, 70, 58), width=2)
    for y in (738, 763, 788):
        d.line((421, y, 523, y + 1), fill=(108, 91, 70, 58), width=2)
    d.line((418, 807, 525, 800), fill=(90, 78, 65, 95), width=4)
    draw_waterline(d, 420, 819, 520, (80, 108, 114, 80))

    return soft_paste(img, layer, blur=1.15)


def option_bridge_arch(base: Image.Image) -> Image.Image:
    img = base.copy().convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")

    arch_box = (390, 620, 554, 806)
    d.arc(arch_box, 180, 360, fill=(165, 122, 85, 155), width=22)
    d.arc((405, 648, 539, 806), 180, 360, fill=(238, 224, 192, 145), width=12)
    d.line((394, 715, 394, 814), fill=(130, 99, 76, 130), width=12)
    d.line((551, 715, 551, 814), fill=(130, 99, 76, 130), width=12)
    d.rectangle((385, 804, 560, 822), fill=(147, 111, 84, 115))

    # Open center so the train/rails read as passing through the arch.
    d.arc((416, 676, 528, 816), 180, 360, fill=(42, 54, 56, 130), width=18)
    d.rectangle((429, 739, 516, 814), fill=(53, 70, 72, 112))
    d.line((398, 695, 548, 690), fill=(95, 76, 63, 90), width=4)
    for x in (410, 438, 468, 498, 528):
        d.line((x, 712, x, 817), fill=(113, 88, 70, 80), width=2)
    for y in (728, 754, 780):
        d.line((397, y, 553, y + 1), fill=(109, 84, 66, 78), width=2)
    draw_waterline(d, 404, 827, 545, (82, 110, 116, 105))

    return soft_paste(img, layer)


def option_bridge_arch_refined(base: Image.Image) -> Image.Image:
    img = base.copy().convert("RGBA")
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")

    # Wider, lighter masonry span with a clearer dark opening.
    d.arc((379, 625, 566, 810), 180, 360, fill=(163, 121, 83, 115), width=18)
    d.arc((398, 651, 548, 812), 180, 360, fill=(232, 215, 181, 108), width=11)
    d.line((383, 714, 383, 814), fill=(130, 96, 73, 88), width=9)
    d.line((562, 714, 562, 814), fill=(130, 96, 73, 88), width=9)
    d.rectangle((379, 806, 566, 820), fill=(147, 111, 84, 83))

    d.arc((416, 685, 529, 820), 180, 360, fill=(41, 54, 56, 118), width=15)
    d.rectangle((430, 746, 516, 813), fill=(51, 68, 70, 90))
    d.line((360, 781, 454, 763), fill=(44, 52, 53, 102), width=3)
    d.line((362, 796, 463, 780), fill=(44, 52, 53, 92), width=3)
    d.line((394, 695, 552, 691), fill=(98, 78, 61, 62), width=3)
    for x in (405, 435, 466, 497, 530):
        d.line((x, 714, x, 817), fill=(113, 88, 70, 48), width=2)
    for y in (730, 756, 782):
        d.line((393, y, 555, y + 1), fill=(109, 84, 66, 52), width=2)
    draw_waterline(d, 405, 824, 548, (82, 110, 116, 75))

    return soft_paste(img, layer, blur=1.05)


def label(image: Image.Image, title: str, body: str) -> Image.Image:
    pad = 28
    header = 88
    out = Image.new("RGB", (image.width + pad * 2, image.height + header + pad), "white")
    d = ImageDraw.Draw(out)
    d.text((pad, 18), title, font=TITLE, fill=(23, 25, 30))
    d.text((pad, 53), body, font=BODY, fill=(72, 78, 86))
    out.paste(image.convert("RGB"), (pad, header))
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    base = Image.open(BASE).convert("RGBA")

    tunnel = option_tunnel(base)
    bridge = option_bridge_arch(base)
    tunnel_refined = option_tunnel_refined(base)
    bridge_refined = option_bridge_arch_refined(base)

    tunnel_path = OUT / "option-a-tunnel-portal-artwork.png"
    bridge_path = OUT / "option-b-bridge-arch-artwork.png"
    tunnel_refined_path = OUT / "option-a2-refined-tunnel-portal-artwork.png"
    bridge_refined_path = OUT / "option-b2-refined-bridge-arch-artwork.png"
    tunnel.save(tunnel_path)
    bridge.save(bridge_path)
    tunnel_refined.save(tunnel_refined_path)
    bridge_refined.save(bridge_refined_path)

    labelled_a = label(tunnel, "A - Tunnel Portal", "Dark portal added where the train exits the left door-flap area.")
    labelled_b = label(bridge, "B - Bridge Arch", "Masonry arch added so the train appears to pass through infrastructure.")
    sheet = Image.new("RGB", (labelled_a.width + labelled_b.width + 24, max(labelled_a.height, labelled_b.height)), "white")
    sheet.paste(labelled_a, (0, 0))
    sheet.paste(labelled_b, (labelled_a.width + 24, 0))
    sheet_path = OUT / "train-exit-repair-options-side-by-side.png"
    sheet.save(sheet_path)

    labelled_a2 = label(tunnel_refined, "A2 - Refined Tunnel Portal", "Smaller dark opening with rails continuing into it.")
    labelled_b2 = label(bridge_refined, "B2 - Refined Bridge Arch", "Lighter arch with a clearer through-opening for the train.")
    refined_sheet = Image.new(
        "RGB",
        (labelled_a2.width + labelled_b2.width + 24, max(labelled_a2.height, labelled_b2.height)),
        "white",
    )
    refined_sheet.paste(labelled_a2, (0, 0))
    refined_sheet.paste(labelled_b2, (labelled_a2.width + 24, 0))
    refined_sheet_path = OUT / "train-exit-repair-options-refined-side-by-side.png"
    refined_sheet.save(refined_sheet_path)

    print(f"wrote={tunnel_path}")
    print(f"wrote={bridge_path}")
    print(f"wrote={tunnel_refined_path}")
    print(f"wrote={bridge_refined_path}")
    print(f"wrote={sheet_path}")
    print(f"wrote={refined_sheet_path}")


if __name__ == "__main__":
    main()
