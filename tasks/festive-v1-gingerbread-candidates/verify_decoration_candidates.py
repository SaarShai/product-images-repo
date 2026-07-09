#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "tasks" / "festive-v1-gingerbread-candidates"
MASK = TASK / "geometry" / "combined-decoration-mask.png"
OUT = TASK / "outputs" / "generated"
REV = TASK / "outputs" / "reviews"
PROD = Path("/Users/za/Library/CloudStorage/GoogleDrive-saar.shai@gmail.com/My Drive/Wanderland Folder/Files/Products/Screenery/new cutting files/NEW Festive/Images/candidates")

FORBIDDEN = ["house", "village", "bakery", "window", "door", "facade", "chalet", "chimney"]


def count_outside(path: Path, mask: Image.Image) -> int:
    img = Image.open(path).convert("RGBA")
    alpha = img.getchannel("A")
    outside = ImageChops.subtract(alpha, mask)
    return sum(1 for v in outside.getdata() if v > 0)


def main():
    mask = Image.open(MASK).convert("L")
    candidates = sorted(OUT.glob("d*-artwork.png"))
    names_ok = all(not any(word in path.name.lower() for word in FORBIDDEN) for path in candidates)
    report = {"candidate_count": len(candidates), "outside_alpha_pixels": {}, "forbidden_name_terms_absent": names_ok}
    for path in candidates:
        report["outside_alpha_pixels"][path.name] = count_outside(path, mask)
    board = REV / "festive-v1-decoration-candidate-board.png"
    prod_board = PROD / board.name
    report["board_exists"] = board.exists()
    report["production_board_exists"] = prod_board.exists()
    report["production_folder"] = str(PROD)
    report["pass"] = (
        len(candidates) >= 6
        and names_ok
        and all(v == 0 for v in report["outside_alpha_pixels"].values())
        and board.exists()
        and prod_board.exists()
    )
    out = REV / "decoration-verification-report.json"
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
