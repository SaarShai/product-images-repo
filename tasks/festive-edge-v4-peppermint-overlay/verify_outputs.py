#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops
from scipy import ndimage as ndi


BASE = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/edge-v4-watercolor-piped-artwork.png")
PROD = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/candidates")
DEFAULTS = [
    PROD / "edge-v4-peppermint-option-1-highres.png",
    PROD / "edge-v4-peppermint-option-2-highres.png",
]


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def ginger_inner_mask(base: Image.Image) -> np.ndarray:
    arr = np.array(base)
    rgb = arr[..., :3].astype(np.int16)
    a = arr[..., 3] > 0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    ginger = a & (r > 90) & (g > 45) & (b < 190) & ((r - g) > 10) & ((g - b) > 5)
    ginger = ndi.binary_closing(ginger, iterations=2)
    ginger = ndi.binary_fill_holes(ginger)
    return ndi.binary_erosion(ginger, iterations=5)


def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def main() -> int:
    paths = [Path(p) for p in (sys.argv[1:] or DEFAULTS)]
    report = {"paths": [str(p) for p in paths], "checks": [], "ok": True}
    failures: list[str] = []
    if len(paths) != 2:
        failures.append("expected exactly two output paths")

    base = rgba(BASE)
    base_a = np.array(base.getchannel("A"))
    base_mask = base_a > 0
    inner = ginger_inner_mask(base)
    protected = base_mask & ~inner
    hashes = []

    for path in paths:
        item = {"path": str(path)}
        if not path.exists():
            failures.append(f"missing: {path}")
            report["checks"].append(item)
            continue
        if path.resolve().parent != PROD.resolve():
            failures.append(f"not in production candidates folder: {path}")
        if path.suffix.lower() != ".png":
            failures.append(f"not a png: {path}")
        im = rgba(path)
        arr = np.array(im)
        hashes.append(sha16(path))
        diff = ImageChops.difference(base, im)
        diff_arr = np.array(diff)
        changed = np.any(diff_arr != 0, axis=2)
        outside_alpha = int(np.count_nonzero((arr[..., 3] > 0) & ~base_mask))
        alpha_equal = bool(np.array_equal(arr[..., 3], base_a))
        changed_inside_inner = int(np.count_nonzero(changed & inner))
        changed_protected = int(np.count_nonzero(changed & protected))
        protected_frac = changed_protected / max(1, int(np.count_nonzero(protected)))

        item.update(
            size=im.size,
            mode=im.mode,
            sha16=hashes[-1],
            outside_alpha=outside_alpha,
            alpha_equal=alpha_equal,
            changed_inside_inner=changed_inside_inner,
            changed_protected=changed_protected,
            protected_frac=round(protected_frac, 6),
        )
        if im.size != base.size:
            failures.append(f"size mismatch: {path} {im.size} != {base.size}")
        if im.mode != "RGBA":
            failures.append(f"mode mismatch: {path} {im.mode}")
        if outside_alpha != 0:
            failures.append(f"outside alpha spill: {path} {outside_alpha}")
        if not alpha_equal:
            failures.append(f"alpha differs from edge-v4 base: {path}")
        if changed_inside_inner < 50000:
            failures.append(f"too little interior decoration delta: {path} {changed_inside_inner}")
        if protected_frac > 0.003:
            failures.append(f"protected edge/background changed too much: {path} {protected_frac}")
        report["checks"].append(item)

    if len(set(hashes)) != len(hashes):
        failures.append("two options have identical file hashes")
    report["distinct_hashes"] = len(set(hashes)) == len(hashes)
    report["failures"] = failures
    report["ok"] = not failures
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
