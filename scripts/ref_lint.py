#!/usr/bin/env python3
"""ref_lint.py — mechanized reference hygiene gate (ENFORCEMENT-MATRIX rows 2,3,4).

Two independent checks, either one can reject a reference image:

  1. VLM checks (--image): two gpt-4o vision calls, same call pattern as scripts/judge.py
     (key loaded via _falcommon.load_openai_key, never printed):
       (a) readable text / lettering / logo / watermark anywhere in the image?
       (b) an OPEN door, doorway void, or white opening where a door should be?
     Exit 2 if either comes back YES. --dry-run prints the prompts and does NOT call the API.

  2. HOLD-OUT check (--provenance / --target-panel): pure path-pattern logic, no network.
     Rejects a reference whose provenance string looks like a GENERATED output (round*/raws/,
     outputs/, RESULTS/, candidates/, finals/) for the SAME target panel it would be used to
     build style-handle art for (see wiki lesson "hold-out ground-truth style ref"). Collection
     original source art (photos, style-read crops, refs/) always passes. A generated output for
     a DIFFERENT panel than the target also passes (current rule scope).

Usage:
  python3 scripts/ref_lint.py --image ref.png [--dry-run]
  python3 scripts/ref_lint.py --provenance "round3/door/raws/s2.png" --target-panel door
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _falcommon import load_openai_key as load_key
from judge import call, img_part

TEXT_PROMPT = (
    "Is there ANY readable text, lettering, logo, or watermark visible anywhere in this "
    "image? Be literal — even faint, partial, or small text counts. Return ONLY JSON with "
    "keys: text_found (bool), where (str: location/description of the text, or empty string "
    "if none)."
)

DOOR_PROMPT = (
    "This is a children's-book style illustration or reference photo of a building facade. "
    "Question: does the image contain a visible archway or doorway opening that is "
    "empty/open (not filled by a closed door)? Reply ONLY with JSON: "
    "{\"open_door_found\": bool, \"where\": string (description of the opening, or empty "
    "string if none)}."
)

GENERATED_OUTPUT_PATTERNS = [
    "round",   # round1/, round2/, roundN/...
    "raws",
    "raws/",
    "outputs",
    "results",
    "candidates",
    "finals",
]

# Path segments that mark provenance as generated-output rather than collection source art.
GENERATED_SEGMENT_RE = re.compile(
    r"(^|[\\/])(round\d*|raws|outputs|results|candidates|finals)([\\/]|$)",
    re.IGNORECASE,
)


def run_text_check(image_path: str, dry_run: bool) -> dict:
    if dry_run:
        return {"prompt": TEXT_PROMPT, "dry_run": True}
    key = load_key()
    content = [{"type": "text", "text": TEXT_PROMPT}, img_part(image_path)]
    return call([{"role": "user", "content": content}], key)


def run_door_check(image_path: str, dry_run: bool) -> dict:
    if dry_run:
        return {"prompt": DOOR_PROMPT, "dry_run": True}
    key = load_key()
    content = [{"type": "text", "text": DOOR_PROMPT}, img_part(image_path)]
    return call([{"role": "user", "content": content}], key)


def hold_out_violation(provenance: str, target_panel: str) -> bool:
    """True if provenance looks like a generated-output path AND relates to target_panel.

    Collection original source art (photos, style-read/ crops, refs/) is never a violation
    even if it happens to contain the target-panel name as a word (e.g. "door" in a filename
    of a harvested photo) — only paths matching a generated-output segment are considered.
    """
    if not provenance or not target_panel:
        return False
    if not GENERATED_SEGMENT_RE.search(provenance):
        return False
    return target_panel.lower() in provenance.lower()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", help="reference image to run the two VLM checks on")
    ap.add_argument("--dry-run", action="store_true", help="print prompts, no API call")
    ap.add_argument("--provenance", help="provenance string/path for the hold-out check")
    ap.add_argument("--target-panel", help="panel name the reference would be used for")
    args = ap.parse_args()

    if args.image:
        text_result = run_text_check(args.image, args.dry_run)
        door_result = run_door_check(args.image, args.dry_run)
        out = {"text_check": text_result, "door_check": door_result}
        print(json.dumps(out, indent=2))
        if args.dry_run:
            return 0
        if text_result.get("text_found") or door_result.get("open_door_found"):
            return 2
        return 0

    if args.provenance is not None or args.target_panel is not None:
        violation = hold_out_violation(args.provenance or "", args.target_panel or "")
        print(json.dumps({
            "provenance": args.provenance,
            "target_panel": args.target_panel,
            "hold_out_violation": violation,
        }, indent=2))
        return 2 if violation else 0

    ap.error("provide --image and/or --provenance/--target-panel")
    return 2


if __name__ == "__main__":
    sys.exit(main())
