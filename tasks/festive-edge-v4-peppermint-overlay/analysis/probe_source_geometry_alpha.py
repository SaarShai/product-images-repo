#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


EDGE = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/production files/festive/"
    "images/edge-v4-watercolor-piped-artwork.png"
)
STYLED = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/new cutting files/NEW Festive/"
    "images/candidates/styled-v1-peppermint-artwork.png"
)
PREVIEW = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/"
    "Wanderland Folder/Files/Products/Screenery/new cutting files/NEW Festive/"
    "images/candidates/styled-v1-peppermint-preview.png"
)


def label_components(mask: np.ndarray) -> tuple[int, list[tuple[int, int, int, int, int]]]:
    try:
        import cv2  # type: ignore

        n, labels, stats, _ = cv2.connectedComponentsWithStats(
            mask.astype(np.uint8), connectivity=8
        )
        components = []
        for idx in range(1, n):
            x, y, w, h, area = [int(v) for v in stats[idx]]
            components.append((area, x, y, x + w - 1, y + h - 1))
        return len(components), components
    except Exception:
        pass

    try:
        from scipy import ndimage  # type: ignore

        labels, n = ndimage.label(mask, structure=np.ones((3, 3), dtype=int))
        slices = ndimage.find_objects(labels)
        components = []
        for idx, slc in enumerate(slices, start=1):
            if slc is None:
                continue
            ys, xs = slc
            area = int((labels[slc] == idx).sum())
            components.append((area, int(xs.start), int(ys.start), int(xs.stop - 1), int(ys.stop - 1)))
        return len(components), components
    except Exception as exc:
        raise RuntimeError("Need cv2 or scipy for connected-component analysis") from exc


def bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def analyze(name: str, path: Path) -> dict[str, object]:
    img = Image.open(path)
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba)
    alpha = arr[:, :, 3]
    rgb = arr[:, :, :3]
    nonzero = alpha > 0
    component_mask = alpha > 16
    component_count, components = label_components(component_mask)
    large = [c for c in components if c[0] >= 1000]
    medium = [c for c in components if c[0] >= 100]
    transparent = alpha == 0
    hidden_rgb = int((transparent & (rgb.sum(axis=2) > 0)).sum())

    return {
        "name": name,
        "path": path,
        "mode": img.mode,
        "size": img.size,
        "has_alpha": "A" in rgba.getbands(),
        "alpha_min": int(alpha.min()),
        "alpha_max": int(alpha.max()),
        "nonzero_alpha": int(nonzero.sum()),
        "nonzero_bbox": bbox(nonzero),
        "components_alpha_gt_16_total": component_count,
        "components_alpha_gt_16_area_ge_100": len(medium),
        "components_alpha_gt_16_area_ge_1000": len(large),
        "largest_components": sorted(large, reverse=True)[:8],
        "transparent_pixels": int(transparent.sum()),
        "transparent_hidden_rgb_pixels": hidden_rgb,
    }


def fmt_bbox(value: object) -> str:
    if value is None:
        return "none"
    x0, y0, x1, y1 = value  # type: ignore[misc]
    return f"{x0},{y0},{x1},{y1}"


def emit(result: dict[str, object]) -> None:
    w, h = result["size"]  # type: ignore[misc]
    print(f"FILE {result['name']} path={result['path']}")
    print(f"DIM {result['name']} {w}x{h} mode={result['mode']}")
    print(
        f"ALPHA {result['name']} has_alpha={result['has_alpha']} "
        f"min={result['alpha_min']} max={result['alpha_max']} "
        f"nonzero={result['nonzero_alpha']} transparent={result['transparent_pixels']}"
    )
    print(f"BBOX {result['name']} nonzero_alpha={fmt_bbox(result['nonzero_bbox'])}")
    print(
        f"COMPONENTS {result['name']} alpha>16 total={result['components_alpha_gt_16_total']} "
        f"area>=100={result['components_alpha_gt_16_area_ge_100']} "
        f"area>=1000={result['components_alpha_gt_16_area_ge_1000']}"
    )
    largest = ";".join(
        f"area={area}@{x0},{y0},{x1},{y1}"
        for area, x0, y0, x1, y1 in result["largest_components"]  # type: ignore[union-attr]
    )
    print(f"LARGEST {result['name']} {largest or 'none'}")
    if result["name"] == "styled_v1_artwork":
        usable = (
            result["has_alpha"]
            and result["nonzero_alpha"] > 0
            and result["transparent_pixels"] > 0
            and result["components_alpha_gt_16_area_ge_100"] > 0
        )
        print(
            "STYLED_TRANSPARENT_PIXELS "
            f"usable_item_pixels={'yes' if usable else 'no'} "
            "background_should_be_ignored="
            f"{'yes' if result['transparent_pixels'] > 0 else 'no'} "
            f"transparent_hidden_rgb={result['transparent_hidden_rgb_pixels']}"
        )


def main() -> None:
    for name, path in (
        ("edge_v4", EDGE),
        ("styled_v1_artwork", STYLED),
        ("styled_v1_preview", PREVIEW),
    ):
        if not path.exists():
            raise FileNotFoundError(path)
        emit(analyze(name, path))


if __name__ == "__main__":
    main()
