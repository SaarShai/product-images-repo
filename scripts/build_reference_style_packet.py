#!/usr/bin/env python3
"""Build a visual style packet from task reference images.

The packet is for image-generation/style agents. It turns the actual reference
images into attachable evidence: full-panel crops, region crops, accent crops,
texture/edge samples, contact sheets, a manifest, and a style-agent prompt.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


def nonwhite_bbox(image: Image.Image, threshold: int = 246) -> tuple[int, int, int, int]:
    arr = np.asarray(image.convert("RGB"))
    mask = np.any(arr < threshold, axis=2)
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return (0, 0, image.width, image.height)
    return (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def expand_box(
    box: tuple[int, int, int, int], image_size: tuple[int, int], margin: int
) -> tuple[int, int, int, int]:
    width, height = image_size
    x0, y0, x1, y1 = box
    return (max(0, x0 - margin), max(0, y0 - margin), min(width, x1 + margin), min(height, y1 + margin))


def crop_save(image: Image.Image, box: tuple[int, int, int, int], out_path: Path) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    crop = image.crop(box)
    crop.save(out_path)
    return {"path": rel(out_path), "bbox": list(box), "size": list(crop.size)}


def color_hex(rgb: np.ndarray) -> str:
    return "#%02x%02x%02x" % tuple(int(v) for v in rgb[:3])


def palette_from_refs(images: list[Image.Image], max_colors: int = 12) -> list[str]:
    samples = []
    for image in images:
        rgb = image.convert("RGB").resize((220, 80), Image.Resampling.BILINEAR)
        arr = np.asarray(rgb).reshape((-1, 3)).astype(np.float32)
        keep = np.any(arr < 246, axis=1)
        arr = arr[keep]
        if len(arr):
            samples.append(arr)
    if not samples:
        return []

    data = np.concatenate(samples, axis=0)
    # Subsample deterministically to keep k-means fast.
    if len(data) > 12000:
        step = max(1, len(data) // 12000)
        data = data[::step]
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 60, 0.5)
    _compactness, labels, centers = cv2.kmeans(
        data.astype(np.float32),
        max_colors,
        None,
        criteria,
        4,
        cv2.KMEANS_PP_CENTERS,
    )
    counts = np.bincount(labels.flatten(), minlength=max_colors)
    order = np.argsort(-counts)
    return [color_hex(centers[i]) for i in order if counts[i] > 0]


def accent_component_boxes(
    image: Image.Image,
    subject_box: tuple[int, int, int, int],
    max_components: int,
) -> list[tuple[int, int, int, int]]:
    arr = np.asarray(image.convert("RGB"))
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    nonwhite = np.any(arr < 246, axis=2)
    red = (h < 13) | (h > 167)
    yellow = (h >= 15) & (h <= 38)
    mint = (h >= 72) & (h <= 94)
    accent = (red | yellow | mint) & (s > 45) & (v > 80) & nonwhite

    x0, y0, x1, y1 = subject_box
    subject_mask = np.zeros_like(accent, dtype=bool)
    subject_mask[y0:y1, x0:x1] = True
    accent &= subject_mask

    kernel = np.ones((19, 19), np.uint8)
    mask = cv2.dilate(accent.astype(np.uint8) * 255, kernel, iterations=1)
    num, _labels, stats, _centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    candidates: list[tuple[int, tuple[int, int, int, int]]] = []
    image_area = image.width * image.height
    for idx in range(1, num):
        x, y, w, hgt, area = stats[idx]
        if area < 180 or area > image_area * 0.12:
            continue
        box = expand_box((int(x), int(y), int(x + w), int(y + hgt)), image.size, 58)
        bw, bh = box[2] - box[0], box[3] - box[1]
        if bw < 35 or bh < 35:
            continue
        candidates.append((int(area), box))

    candidates.sort(key=lambda item: item[0], reverse=True)
    boxes: list[tuple[int, int, int, int]] = []
    for _area, box in candidates:
        if any(iou(box, existing) > 0.55 for existing in boxes):
            continue
        boxes.append(box)
        if len(boxes) >= max_components:
            break
    return boxes


def iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    return inter / float(area_a + area_b - inter)


def make_contact_sheet(items: list[dict], out_path: Path, title: str) -> None:
    thumbs = []
    for item in items:
        image = Image.open(ROOT / item["path"] if not Path(item["path"]).is_absolute() else item["path"]).convert("RGB")
        image.thumbnail((360, 220), Image.Resampling.LANCZOS)
        thumbs.append((item["label"], image))

    cols = 3
    cell_w, cell_h = 400, 290
    header_h = 62
    rows = max(1, math.ceil(len(thumbs) / cols))
    sheet = Image.new("RGB", (cols * cell_w, header_h + rows * cell_h), (250, 250, 248))
    draw = ImageDraw.Draw(sheet)
    try:
        title_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 28)
        label_font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 17)
    except Exception:
        title_font = label_font = ImageFont.load_default()
    draw.text((24, 18), title, fill=(20, 48, 88), font=title_font)
    for idx, (label, thumb) in enumerate(thumbs):
        col = idx % cols
        row = idx // cols
        x = col * cell_w + 20
        y = header_h + row * cell_h + 20
        draw.rounded_rectangle((x - 8, y - 8, x + cell_w - 32, y + cell_h - 20), radius=8, fill=(255, 255, 255), outline=(220, 224, 228))
        tx = x + (cell_w - 40 - thumb.width) // 2
        sheet.paste(thumb, (tx, y + 22))
        draw.text((x, y + 242), label[:46], fill=(48, 66, 88), font=label_font)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path)


def write_prompt(task_dir: Path, manifest: dict) -> Path:
    prompt_path = task_dir / "prompts" / "prompt-v2-style-packet-elements-first.md"
    attachment_lines = "\n".join(f"- `{item['path']}` - {item['label']}" for item in manifest["agent_attachments"])
    text = f"""# Prompt V2: Style Packet Elements First

Use the attached style packet images as the primary style source. Do not rely on
written style adjectives alone.

## Visual Attachments To Use

{attachment_lines}

## Task

Generate a style-matched element sheet first, not a final template composition.
Create separate control-panel elements that look like they came from the
reference images: dials, sliders, capsule buttons, small bolts, colored pins,
edge/shadow samples, and blue watercolor panel fragments.

## Required Style Match

- Match the actual crops in shape language, line irregularity, watercolor
  bleed, soft highlight placement, outline thickness, shadow pooling, and
  simple friendly object vocabulary.
- Use the palette in `style-packet/style-packet.json`, but do not treat palette
  as the style. The shapes and rendering must also match.
- Keep elements separate on a white or transparent background so geometry agents
  can place them later.
- Do not draw the final SVG contour, diagonal slot, or cutouts. Geometry agents
  handle placement and masks after the style elements are generated.

## Negative Rules

- Do not produce flat vector icons, glossy app UI, hard 3D plastic, photoreal
  metal, dark machinery, or generic blue rectangles.
- Do not crop a full rectangular panel into the template.
- Do not invent a style from memory after reading this prompt. Use the packet
  images directly.

## Handoff

Return an element sheet plus a short note naming which packet crops each element
was based on. The geometry agent will place accepted elements into safe pockets
from `template-manifest.json`.
"""
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(text, encoding="utf-8")
    return prompt_path


def build_packet(task_dir: Path, refs: list[Path], max_components: int) -> dict:
    out_dir = task_dir / "style-packet"
    crops_dir = out_dir / "crops"
    out_dir.mkdir(parents=True, exist_ok=True)
    crops_dir.mkdir(parents=True, exist_ok=True)

    images = [Image.open(path).convert("RGB") for path in refs]
    crop_records: list[dict] = []
    attachment_records: list[dict] = []

    for ref_index, (ref_path, image) in enumerate(zip(refs, images), start=1):
        ref_slug = f"ref{ref_index:02d}-{slug(ref_path.stem)[:42]}"
        subject = expand_box(nonwhite_bbox(image), image.size, 18)

        full = crop_save(image, subject, crops_dir / f"{ref_slug}-full-panel.png")
        full.update({"label": f"ref {ref_index} full panel", "type": "full-panel", "source": rel(ref_path)})
        crop_records.append(full)
        attachment_records.append(full)

        sx0, sy0, sx1, sy1 = subject
        sw, sh = sx1 - sx0, sy1 - sy0
        sections = [
            ("left-region", (sx0, sy0, sx0 + int(sw * 0.38), sy1)),
            ("center-region", (sx0 + int(sw * 0.31), sy0, sx0 + int(sw * 0.70), sy1)),
            ("right-region", (sx0 + int(sw * 0.62), sy0, sx1, sy1)),
            ("body-texture", (sx0 + int(sw * 0.40), sy0 + int(sh * 0.28), sx0 + int(sw * 0.62), sy0 + int(sh * 0.72))),
            ("edge-treatment", (sx0, sy0, sx0 + int(sw * 0.24), sy0 + int(sh * 0.42))),
        ]
        for section_label, box in sections:
            record = crop_save(image, expand_box(box, image.size, 8), crops_dir / f"{ref_slug}-{section_label}.png")
            record.update({"label": f"ref {ref_index} {section_label}", "type": section_label, "source": rel(ref_path)})
            crop_records.append(record)
            if section_label in {"left-region", "center-region", "right-region", "body-texture", "edge-treatment"}:
                attachment_records.append(record)

        for comp_index, box in enumerate(accent_component_boxes(image, subject, max_components), start=1):
            record = crop_save(image, box, crops_dir / f"{ref_slug}-accent-component-{comp_index:02d}.png")
            record.update({"label": f"ref {ref_index} accent component {comp_index:02d}", "type": "accent-component", "source": rel(ref_path)})
            crop_records.append(record)
            attachment_records.append(record)

    # Keep the attachment set strong but not overwhelming.
    priority = {"full-panel": 0, "left-region": 1, "center-region": 1, "right-region": 1, "body-texture": 2, "edge-treatment": 2, "accent-component": 3}
    attachment_records = sorted(attachment_records, key=lambda item: (priority.get(item["type"], 9), item["label"]))[:24]

    make_contact_sheet(
        [{"path": rel(path), "label": f"source ref {idx}"} for idx, path in enumerate(refs, start=1)],
        out_dir / "reference-contact-sheet.png",
        "Source style references",
    )
    make_contact_sheet(crop_records[:30], out_dir / "style-exemplar-sheet.png", "Style packet exemplars")

    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "task": task_dir.name,
        "purpose": "visual style packet for image-generation/style agents",
        "source_refs": [rel(path) for path in refs],
        "contact_sheets": {
            "reference_contact_sheet": rel(out_dir / "reference-contact-sheet.png"),
            "style_exemplar_sheet": rel(out_dir / "style-exemplar-sheet.png"),
        },
        "palette_hex": palette_from_refs(images),
        "crops": crop_records,
        "agent_attachments": attachment_records,
        "agent_contract": [
            "Attach packet images when asking a style agent to generate elements.",
            "Generate style-matched element sheets before geometry placement.",
            "Reject outputs that only match palette while missing watercolor edge, line, lighting, and object vocabulary.",
            "Geometry agents place accepted elements into SVG safe pockets after style generation.",
        ],
    }

    (out_dir / "style-packet.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    readme = f"""# Reference Style Packet

This packet is built from the actual reference images. Use it for style/image-gen
agents before any geometry placement.

## Main Files

- `{manifest['contact_sheets']['reference_contact_sheet']}`
- `{manifest['contact_sheets']['style_exemplar_sheet']}`
- `style-packet/style-packet.json`
- `prompts/prompt-v2-style-packet-elements-first.md`

## Agent Rule

Style agents must use the packet images directly. Written descriptions are only
secondary labels. Geometry agents should receive generated element sheets and
the SVG/template manifest separately.
"""
    (out_dir / "README.md").write_text(readme, encoding="utf-8")
    prompt_path = write_prompt(task_dir, manifest)
    manifest["prompt"] = rel(prompt_path)
    (out_dir / "style-packet.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--refs", nargs="*", type=Path, default=None, help="Override task refs.")
    parser.add_argument("--max-components", type=int, default=8, help="Accent component crops per reference.")
    args = parser.parse_args()

    task_dir = args.task_dir
    if not task_dir.is_absolute():
        task_dir = ROOT / task_dir
    task_dir = task_dir.resolve()
    if not task_dir.exists():
        raise SystemExit(f"Task directory does not exist: {task_dir}")

    if args.refs:
        refs = [path.expanduser().resolve() for path in args.refs]
    else:
        refs = sorted(path.resolve() for path in (task_dir / "refs").iterdir() if path.suffix.lower() in IMAGE_EXTS)
    missing = [str(path) for path in refs if not path.exists()]
    if missing:
        raise SystemExit("Missing reference image(s):\n" + "\n".join(f"- {item}" for item in missing))
    if not refs:
        raise SystemExit(f"No reference images found in {task_dir / 'refs'}")

    manifest = build_packet(task_dir, refs, args.max_components)
    print(rel(task_dir / "style-packet"))
    print(f"crops={len(manifest['crops'])} attachments={len(manifest['agent_attachments'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
