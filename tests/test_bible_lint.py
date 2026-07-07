import copy
from pathlib import Path

import yaml

from scripts.bible_lint import lint_bible


REPO_ROOT = Path(__file__).resolve().parents[1]
BIBLE = REPO_ROOT / "tasks/marriott-hospital/style-spec/bible-v1.yaml"


def test_migrated_bible_lints_without_errors():
    result = lint_bible(BIBLE, repo_root=REPO_ROOT)

    assert result.exit_code in {0, 1}
    assert not result.errors


def test_missing_ref_path_exits_2(tmp_path):
    data = _load_bible_data()
    data["refs_by_role"]["content_only"] = [
        "tasks/marriott-hospital/style-read/does-not-exist.png"
    ]
    bible = _write_yaml(tmp_path, data)

    result = lint_bible(bible, repo_root=REPO_ROOT)

    assert result.exit_code == 2
    assert any(
        "missing ref file" in check.detail
        for check in result.checks
        if check.status == "FAIL"
    )


def test_duplicate_ref_path_across_roles_exits_2(tmp_path):
    data = _load_bible_data()
    duplicate = data["refs_by_role"]["architecture_anchor"][0]
    data["refs_by_role"]["medium_anchor"] = [
        *data["refs_by_role"]["medium_anchor"],
        duplicate,
    ]
    bible = _write_yaml(tmp_path, data)

    result = lint_bible(bible, repo_root=REPO_ROOT)

    assert result.exit_code == 2
    assert any(
        "appears in architecture_anchor and medium_anchor" in check.detail
        for check in result.checks
        if check.status == "FAIL"
    )


def _load_bible_data():
    with BIBLE.open("r", encoding="utf-8") as handle:
        return copy.deepcopy(yaml.safe_load(handle))


def _write_yaml(tmp_path, data):
    bible = tmp_path / "synthetic-bible.yaml"
    bible.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return bible
