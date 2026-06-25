#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
BASE = Path("tasks/berlin-hotel-base/wave3_tower_foreground_repair/shortlist/s09_openai_bounded_external.png")
LOCAL_DIR = ROOT / "local_variants"
EXT_DIR = ROOT / "external"
RESULTS = ROOT / "results"
EXT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)

MASK = RESULTS / "wave4_issue_mask_feathered.png"
MASK_HARD = RESULTS / "wave4_issue_mask_hardish.png"

SS_W, SS_H = 2112, 1468
FULL_W, FULL_H = Image.open(BASE).size
Y0 = 439.0
SCALE = FULL_W / SS_W

REGIONS = [
    ("gate_train_wisp_l", (320, 1088, 396, 1205)),
    ("gate_train_wisp_m", (430, 1072, 506, 1198)),
    ("gate_train_wisp_r", (500, 1050, 610, 1212)),
    ("bridge_white_sign", (1000, 1122, 1120, 1192)),
    ("church_base_portal", (1284, 940, 1460, 1124)),
    ("right_mid_haze", (1490, 1055, 1656, 1262)),
    ("hotel_roof_wipe", (1772, 350, 1882, 520)),
    ("hotel_ground_black", (1846, 1210, 1992, 1322)),
    ("far_right_sliver", (2040, 1125, 2112, 1328)),
]


def ss_to_full(box: tuple[int, int, int, int], pad: int = 12) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (
        max(0, int(round(x0 * SCALE)) - pad),
        max(0, int(round(y0 * SCALE + Y0)) - pad),
        min(FULL_W, int(round(x1 * SCALE)) + pad),
        min(FULL_H, int(round(y1 * SCALE + Y0)) + pad),
    )


FULL_REGIONS = [(name, ss_to_full(box)) for name, box in REGIONS]


def normalize_donor(raw: Path) -> Image.Image:
    donor = Image.open(raw).convert("RGB")
    if donor.size != (FULL_W, FULL_H):
        donor = donor.resize((FULL_W, FULL_H), Image.Resampling.LANCZOS)
    return donor


def composite(raw: Path, out: Path, mask_path: Path = MASK) -> None:
    base = Image.open(BASE).convert("RGB")
    donor = normalize_donor(raw)
    mask = Image.open(mask_path).convert("L").resize((FULL_W, FULL_H), Image.Resampling.LANCZOS)
    Image.composite(donor, base, mask).save(out)


def build_crop_board(paths: list[tuple[str, Path]], out: Path) -> None:
    tile_w, tile_h = 260, 180
    label_h = 34
    gap = 10
    board = Image.new(
        "RGB",
        (len(FULL_REGIONS) * tile_w + (len(FULL_REGIONS) + 1) * gap, len(paths) * (tile_h + label_h) + (len(paths) + 1) * gap),
        "white",
    )
    draw = ImageDraw.Draw(board)
    for r, (label, p) in enumerate(paths):
        im = Image.open(p).convert("RGB")
        ybase = gap + r * (tile_h + label_h + gap)
        draw.text((gap, ybase), label, fill=(140, 0, 0))
        for c, (name, (x0, y0, x1, y1)) in enumerate(FULL_REGIONS):
            crop = im.crop((x0, y0, x1, y1))
            crop.thumbnail((tile_w, tile_h), Image.Resampling.LANCZOS)
            x = gap + c * (tile_w + gap)
            y = ybase + label_h
            board.paste(crop, (x, y))
            draw.rectangle((x, y, x + tile_w - 1, y + tile_h - 1), outline=(210, 210, 210))
            if r == 0:
                draw.text((x + 3, y + 3), name, fill=(0, 70, 120))
    board.save(out)


def build_context_board(paths: list[tuple[str, Path]], out: Path) -> None:
    cols = 2
    thumb_w = 860
    label_h = 40
    gap = 20
    rows = (len(paths) + cols - 1) // cols
    thumb_h = round(thumb_w * SS_H / SS_W)
    board = Image.new("RGB", (cols * thumb_w + (cols + 1) * gap, rows * (thumb_h + label_h) + (rows + 1) * gap), "white")
    draw = ImageDraw.Draw(board)
    crop_y0 = int(round(Y0))
    crop_y1 = int(round(Y0 + SS_H * SCALE))
    for i, (label, p) in enumerate(paths):
        im = Image.open(p).convert("RGB")
        visible = im.crop((0, crop_y0, FULL_W, crop_y1)).resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = gap + (i % cols) * (thumb_w + gap)
        y = gap + (i // cols) * (thumb_h + label_h + gap)
        draw.text((x, y), label, fill=(140, 0, 0))
        board.paste(visible, (x, y + label_h))
    board.save(out)


def verify(paths: list[tuple[str, Path]]) -> None:
    base = np.array(Image.open(BASE).convert("RGB"))
    allowed = np.array(Image.open(MASK_HARD).convert("L")) > 0
    lines = []
    for label, p in paths:
        if label == "base":
            continue
        im = np.array(Image.open(p).convert("RGB"))
        diff = np.abs(im.astype(int) - base.astype(int)).max(axis=2) > 2
        lines.append(f"{label}\tinside_changed={int((diff & allowed).sum())}\toutside_changed={int((diff & ~allowed).sum())}\tpath={p}")
    (RESULTS / "wave4_feedback_verification.txt").write_text("\n".join(lines) + "\n")


def main() -> None:
    candidates: list[tuple[str, Path]] = [
        ("base", BASE),
        ("v01 source donor all circled", LOCAL_DIR / "v01_source_donor_all_circled.png"),
        ("v02 source nonhotel + banked hotel", LOCAL_DIR / "v02_source_nonhotel_banked_hotel.png"),
        ("v03 local inpaint all circled", LOCAL_DIR / "v03_telea_inpaint_all_circled.png"),
        ("v04 soft wash + source details", LOCAL_DIR / "v04_soft_wash_plus_source_detail.png"),
        ("v05 hybrid source + targeted inpaint", LOCAL_DIR / "v05_hybrid_source_detail_inpaint_wisps_hotel.png"),
    ]
    raw_to_label = [
        ("v06 OpenAI artifact repair donor", EXT_DIR / "openai_artifact_repair_raw.png", EXT_DIR / "v06_openai_artifact_repair_masked.png"),
        ("v07 OpenAI watercolor reconstruct donor", EXT_DIR / "openai_watercolor_reconstruct_raw.png", EXT_DIR / "v07_openai_watercolor_reconstruct_masked.png"),
    ]
    for label, raw, out in raw_to_label:
        if raw.exists():
            composite(raw, out)
            candidates.append((label, out))
    hybrids = [
        ("v08 OpenAI watercolor tight", ROOT / "hybrids" / "v08_openai_watercolor_tight.png"),
        ("v09 OpenAI watercolor soft alpha", ROOT / "hybrids" / "v09_openai_watercolor_soft_alpha.png"),
        ("v10 mixed OpenAI nonhotel/artifact hotel", ROOT / "hybrids" / "v10_mixed_openai_nonhotel_artifact_hotel.png"),
        ("v11 mixed OpenAI very safe", ROOT / "hybrids" / "v11_mixed_openai_very_safe.png"),
    ]
    candidates.extend(hybrids)

    existing = [(label, p) for label, p in candidates if p.exists()]
    build_crop_board(existing, RESULTS / "wave4_feedback_detail_board.png")
    build_context_board(existing, RESULTS / "wave4_feedback_context_board.png")
    verify(existing)


if __name__ == "__main__":
    main()
