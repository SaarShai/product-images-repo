#!/usr/bin/env python3
"""emblem_gate.py — VLM motif-count + required-prop presence gate.

Companion to judge.py, but scoped to the feature-callouts contract instead of
generic wellformedness: a candidate panel can be cleanly painted and STILL fail
the brief if it has two cross badges instead of one, or is missing a must-have
prop (LAW 0 fidelity, not aesthetics).

Reads a feature-callouts YAML (see tasks/marriott-hospital/style-spec/
feature-callouts-v1.yaml) and turns it into a rule set:
  - one count rule per feature (feature_id, expected count, priority)
  - the `avoid` string carried through verbatim (e.g. "not a second cross
    badge" / "exactly ONE") since count-confusable motifs (beacon vs badge:
    the beacon is a LAMP, not a badge) need that context in the prompt, not
    just a bare number
  - negative_callouts carried through as global avoid-rules
  - a presence check for every priority:must feature

The VLM is always shown the WHOLE image (never tiles): tiling hides
duplicates across a seam (wiki: judge-needs-hidpi-crops finding).

CLI:
  python3 scripts/emblem_gate.py --image cand.png --callouts callouts.yaml [--dry-run]

Output: strict JSON {motif_counts, presence, violations[], pass} on stdout.
Exit 0 (pass, no violations) or 2 (fail / violations found).
--dry-run prints the assembled prompt + parsed rules (no API call, no network).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from judge import call, img_part  # reuse the OpenAI vision call pattern
from _falcommon import load_openai_key as load_key

MODEL_HINT = "gpt-4o"  # matches judge.py's MODEL; kept as a named constant here for the prompt text


def parse_callouts(path) -> dict:
    """Load a feature-callouts YAML into a flat rule set.

    Returns {"motif_rules": [...], "must_features": [...], "negative_callouts": [...]}.
    Each motif_rule: {feature_id, name, count, priority, avoid, layer}.
    """
    data = yaml.safe_load(Path(path).read_text())
    features = data.get("features", []) or []
    motif_rules = []
    must_features = []
    for f in features:
        rule = {
            "feature_id": f.get("feature_id"),
            "name": f.get("name", f.get("feature_id")),
            "count": f.get("count", 1),
            "priority": f.get("priority", "nice"),
            "avoid": f.get("avoid", ""),
            "layer": f.get("layer"),
        }
        motif_rules.append(rule)
        if rule["priority"] == "must":
            must_features.append(rule)
    return {
        "panel": data.get("panel"),
        "contract": data.get("contract"),
        "motif_rules": motif_rules,
        "must_features": must_features,
        "negative_callouts": data.get("negative_callouts", []) or [],
    }


def build_prompt(rules: dict) -> tuple[str, str]:
    """Return (system_prompt, user_text) for the VLM call."""
    motif_lines = []
    for r in rules["motif_rules"]:
        line = f"- {r['feature_id']} ({r['name']}): expected count = {r['count']}, priority = {r['priority']}"
        if r["avoid"]:
            line += f". AVOID: {r['avoid']}"
        motif_lines.append(line)

    must_lines = [f"- {r['feature_id']} ({r['name']})" for r in rules["must_features"]]
    neg_lines = [f"- {n}" for n in rules["negative_callouts"]]

    sys_p = (
        "You are a strict QA judge counting toy-illustration motifs on a die-cut "
        "children's-book panel. Inspect the WHOLE image at once (never reason about "
        "cropped tiles) so you do not miss duplicate motifs that straddle different "
        "areas of the panel. For EACH motif rule below, report how many instances you "
        "actually see, comparing against the expected count. Watch for count-confusable "
        "motifs called out with an AVOID note (e.g. a rooftop cross-BEACON is a LAMP "
        "fixture, not a second cross-BADGE — do not conflate the two when counting). "
        "Then check presence of every MUST-priority feature. Return ONLY JSON with keys: "
        "motif_counts (object: feature_id -> {seen: int, expected: int, match: bool}), "
        "presence (object: feature_id -> bool, for every MUST feature), "
        "violations (list of strings: any count mismatch, missing MUST feature, or "
        "negative-callout breach, in plain language), pass (bool: true iff no violations)."
    )

    user_text_lines = ["MOTIF RULES (count each, whole image):", *motif_lines, ""]
    if must_lines:
        user_text_lines += ["MUST-PRESENT FEATURES (check each is present):", *must_lines, ""]
    if neg_lines:
        user_text_lines += ["NEGATIVE CALLOUTS (global avoid-rules):", *neg_lines, ""]
    user_text_lines.append(
        "Assess the attached image against all of the above and return the JSON verdict."
    )
    return sys_p, "\n".join(user_text_lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image", required=True, help="candidate panel PNG/JPG")
    ap.add_argument("--callouts", required=True, help="feature-callouts YAML")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the assembled VLM prompt + parsed rules, no API call")
    a = ap.parse_args()

    rules = parse_callouts(a.callouts)
    sys_p, user_text = build_prompt(rules)

    if a.dry_run:
        print(json.dumps({
            "dry_run": True,
            "image": a.image,
            "callouts": a.callouts,
            "rules": rules,
            "system_prompt": sys_p,
            "user_text": user_text,
        }, indent=2))
        raise SystemExit(0)

    key = load_key()
    content = [{"type": "text", "text": user_text}, img_part(a.image)]
    out = call([{"role": "system", "content": sys_p}, {"role": "user", "content": content}], key)

    print(json.dumps(out, indent=2))
    raise SystemExit(0 if out.get("pass") else 2)


if __name__ == "__main__":
    main()
