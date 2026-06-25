#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def valid(path: Path) -> tuple[bool, list[int] | None, str]:
    try:
        if not path.exists():
            return False, None, "missing"
        with Image.open(path) as img:
            img.verify()
        with Image.open(path) as img:
            size = [img.width, img.height]
        if size[0] < 64 or size[1] < 64:
            return False, size, "too_small"
        return True, size, "ok"
    except Exception as exc:
        return False, None, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    rows = []
    for line in args.manifest.read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    failures = []
    for row in rows:
        ok, size, reason = valid(Path(row["output"]))
        row["validated"] = ok
        row["validated_size"] = size
        row["validation_reason"] = reason
        if not ok:
            failures.append(row)
    print(json.dumps({"rows": len(rows), "failures": len(failures)}, indent=2))
    if failures:
        print(json.dumps(failures, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
