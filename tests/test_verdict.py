"""tests/test_verdict.py — verdict_form.py + verdict_apply.py round-trip.

Generates a form, fills it via string replace (simulating the user's inline
edits), applies it, and asserts the JSON round-trips. Also covers the
tolerant-default path (unanswered form) and the additive bible-patch rule.
"""
import json

import pytest

import scripts.verdict_form as VF
import scripts.verdict_apply as VA


def _fill(text: str, **edits: str) -> str:
    """Apply a series of exact string replacements to a generated form."""
    for old, new in edits.items():
        assert old in text, f"expected placeholder not found: {old!r}"
        text = text.replace(old, new)
    return text


def test_form_generation_is_one_screen():
    text = VF.build_form("r17", ["outputs/a.png", "outputs/b.png"], gate="cleanup",
                          decisions=["door: clean|ornate|noleafcross"],
                          ab="canopy too dense?")
    # candidate links use the FILENAME as link text (repo-wide rule)
    assert "- [a.png](outputs/a.png)" in text
    assert "- [b.png](outputs/b.png)" in text
    for key, label in VF.AXES:
        assert f"[{key}]" in text
    assert "one of: " + " / ".join(VF.RETAKE_LABELS) in text
    assert "one of: " + " / ".join(VF.NEXT_ACTIONS) in text
    # short: comfortably fits one terminal screen
    assert len(text.splitlines()) <= 45


def test_round_trip_all_fields():
    text = VF.build_form("r17", ["outputs/a.png", "outputs/b.png"], gate="cleanup",
                          decisions=["door: clean|ornate|noleafcross"],
                          ab="canopy too dense?")
    filled = _fill(
        text,
        **{
            "- Motifs/small elements (crop ids) [motifs]: approve / retake\n  note:":
                "- Motifs/small elements (crop ids) [motifs]: retake\n  note: cross badge #2 wrong form, crop c3",
            "label:": "label: CLEANUP_RETAKE",
            "- door [clean|ornate|noleafcross]: ": "- door [clean|ornate|noleafcross]: clean",
            "A / B is closer because:": "A / B is closer because: A, tighter to the die-cut",
            "next_action:": "next_action: local repair",
            "## Must preserve\n": "## Must preserve\nleft facade, door frame\n",
            "## May change\n": "## May change\ncanopy density\n",
        },
    )

    verdict = VA.parse_form(filled)

    assert verdict["round"] == "r17"
    assert verdict["gate"] == "cleanup"
    assert verdict["candidates"] == ["outputs/a.png", "outputs/b.png"]

    assert verdict["axes"]["motifs"]["verdict"] == "retake"
    assert verdict["axes"]["motifs"]["note"] == "cross badge #2 wrong form, crop c3"
    for key in ("style_family", "geometry", "palette_finish", "prepress"):
        assert verdict["axes"][key]["verdict"] == "approve"
        assert verdict["axes"][key]["note"] == ""

    assert verdict["retake_label"] == "CLEANUP_RETAKE"
    assert verdict["decisions"] == {"door": "clean"}
    assert verdict["ab"] == {
        "question": "canopy too dense?",
        "pick": "A",
        "reason": "A, tighter to the die-cut",
    }
    assert verdict["next_action"] == "local repair"
    assert verdict["must_preserve"] == ["left facade, door frame"]
    assert verdict["may_change"] == ["canopy density"]

    # must be JSON-serializable end to end (what the CLI prints to stdout)
    json.dumps(verdict)


def test_unanswered_form_defaults_sanely():
    text = VF.build_form("r18", ["x.png"], gate="rough")

    verdict = VA.parse_form(text)

    assert all(a["verdict"] == "approve" for a in verdict["axes"].values())
    assert all(a["note"] == "" for a in verdict["axes"].values())
    assert verdict["retake_label"] is None
    assert verdict["decisions"] == {}
    assert verdict["ab"] is None
    assert verdict["must_preserve"] == []
    assert verdict["may_change"] == []
    # no axis said retake -> infer "accept"
    assert verdict["next_action"] == "accept"


def test_retake_axis_without_explicit_next_action_infers_phase_retake():
    text = VF.build_form("r19", ["x.png"])
    filled = _fill(
        text,
        **{
            "- Geometry/template [geometry]: approve / retake\n  note:":
                "- Geometry/template [geometry]: retake\n  note: door arch pinched",
        },
    )

    verdict = VA.parse_form(filled)

    assert verdict["axes"]["geometry"]["verdict"] == "retake"
    assert verdict["next_action"] == "phase retake"


def test_next_action_unresolvable_raises():
    text = VF.build_form("r20", ["x.png"])
    filled = _fill(text, **{"next_action:": "next_action: maybe kinda"})

    with pytest.raises(ValueError):
        VA.parse_form(filled)


def test_cli_exit_code_2_on_unresolvable_next_action(tmp_path):
    import subprocess
    import sys
    from pathlib import Path as _P

    repo_root = _P(__file__).resolve().parents[1]
    form_path = tmp_path / "VERDICT-r21.md"
    text = VF.build_form("r21", ["x.png"])
    form_path.write_text(_fill(text, **{"next_action:": "next_action: maybe kinda"}))

    proc = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "verdict_apply.py"), str(form_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 2


def test_bible_patch_is_additive(tmp_path):
    bible = tmp_path / "bible.yaml"
    bible.write_text("mood_words:\n  must: [\"playful\"]\n")
    original = bible.read_text()

    text = VF.build_form("r17", ["x.png"])
    filled = _fill(
        text,
        **{
            "- Motifs/small elements (crop ids) [motifs]: approve / retake\n  note:":
                "- Motifs/small elements (crop ids) [motifs]: retake\n  note: cross badge wrong form",
        },
    )
    verdict = VA.parse_form(filled)

    changed = VA.apply_bible_patch(bible, verdict)

    assert changed is True
    new_content = bible.read_text()
    assert new_content.startswith(original)
    assert "# VERDICT-PATCH (r17, motifs): cross badge wrong form" in new_content


def test_bible_patch_noop_when_no_retake_notes(tmp_path):
    bible = tmp_path / "bible.yaml"
    bible.write_text("mood_words:\n  must: [\"playful\"]\n")
    original = bible.read_text()

    text = VF.build_form("r22", ["x.png"])
    verdict = VA.parse_form(text)  # all approve, no notes

    changed = VA.apply_bible_patch(bible, verdict)

    assert changed is False
    assert bible.read_text() == original
