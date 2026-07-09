from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image


TASK_DIR = Path("tasks/festive-magenta-m5-upscale")
MANIFEST = TASK_DIR / "pilot-manifest.json"
PROD_CANDIDATES = Path(
    "/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/production files/festive/images/Images/candidates"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def magenta_fg_pct(rgba: np.ndarray) -> float:
    rgb = rgba[..., :3]
    alpha = rgba[..., 3] > 15
    if not np.any(alpha):
        return 100.0
    magenta = (rgb[..., 0] > 185) & (rgb[..., 1] < 105) & (rgb[..., 2] > 155)
    return float(np.count_nonzero(magenta & alpha) / np.count_nonzero(alpha) * 100)


def main() -> None:
    failures: list[str] = []
    if not MANIFEST.exists():
        raise SystemExit(f"FAIL manifest missing: {MANIFEST}")
    data = json.loads(MANIFEST.read_text())
    report = {"pilots": [], "boards": {}, "failures": failures}

    for item in data.get("pilots", []):
        source = Path(item["source"])
        output = Path(item["output"])
        if not source.exists():
            failures.append(f"missing source {source}")
            continue
        if not output.exists():
            failures.append(f"missing output {output}")
            continue
        if not str(output).startswith(str(PROD_CANDIDATES)):
            failures.append(f"output outside production candidates {output}")

        src_size = tuple(item["source_size"])
        expected = (src_size[0] * data["scale"], src_size[1] * data["scale"])
        im = Image.open(output).convert("RGBA")
        rgba = np.array(im)
        source_sha = sha256(source)
        if item["source_sha_before"] != item["source_sha_after"] or source_sha != item["source_sha_before"]:
            failures.append(f"source hash changed {source.name}")
        if im.size != expected:
            failures.append(f"{output.name} size {im.size} != expected {expected}")
        if im.mode != "RGBA":
            failures.append(f"{output.name} mode {im.mode} != RGBA")
        alpha_nonzero = int(np.count_nonzero(rgba[..., 3] > 0))
        if alpha_nonzero == 0:
            failures.append(f"{output.name} has empty alpha")
        magenta_pct = magenta_fg_pct(rgba)
        if magenta_pct > 0.5:
            failures.append(f"{output.name} foreground magenta-like pixels too high: {magenta_pct:.3f}%")
        report["pilots"].append(
            {
                "output": str(output),
                "size": list(im.size),
                "expected": list(expected),
                "alpha_nonzero": alpha_nonzero,
                "magenta_fg_pct": round(magenta_pct, 4),
                "source_hash_unchanged": source_sha == item["source_sha_before"],
            }
        )

    for key, value in data.get("boards", {}).items():
        path = Path(value)
        exists = path.exists()
        report["boards"][key] = {"path": str(path), "exists": exists}
        if not exists:
            failures.append(f"missing board {key}: {path}")
        elif not str(path).startswith(str(PROD_CANDIDATES)):
            failures.append(f"board outside production candidates {path}")

    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
