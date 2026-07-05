import json

import pytest

from studio.library import add_result, query


def test_add_then_query_roundtrip(tmp_path):
    lib_dir = tmp_path / "lib"
    image = tmp_path / "candidate.png"
    image.write_bytes(b"candidate-one")

    result_id = add_result(lib_dir, image, {"task": "T8", "panel": "door"})
    matches = query(lib_dir, task="T8")

    assert matches[0]["id"] == result_id
    assert matches[0]["orig_name"] == "candidate.png"
    assert matches[0]["meta"]["panel"] == "door"
    assert len(list((lib_dir / "objects").iterdir())) == 1


def test_same_content_added_twice_produces_one_object_and_two_jsonl_rows(tmp_path):
    lib_dir = tmp_path / "lib"
    image = tmp_path / "candidate.png"
    image.write_bytes(b"same-content")

    first_id = add_result(lib_dir, image, {"task": "T8", "route": "first"})
    second_id = add_result(lib_dir, image, {"task": "T8", "route": "second"})

    assert second_id == first_id
    assert len(list((lib_dir / "objects").iterdir())) == 1
    lines = (lib_dir / "results.jsonl").read_text().splitlines()
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    assert [record["meta"]["route"] for record in records] == ["first", "second"]


def test_different_content_same_filename_produces_two_objects(tmp_path):
    lib_dir = tmp_path / "lib"
    left_dir = tmp_path / "left"
    right_dir = tmp_path / "right"
    left_dir.mkdir()
    right_dir.mkdir()
    first = left_dir / "candidate.png"
    second = right_dir / "candidate.png"
    first.write_bytes(b"first-content")
    second.write_bytes(b"second-content")

    first_id = add_result(lib_dir, first, {"task": "T8", "variant": 1})
    second_id = add_result(lib_dir, second, {"task": "T8", "variant": 2})

    assert first_id != second_id
    assert len(list((lib_dir / "objects").iterdir())) == 2
    assert len(query(lib_dir, task="T8")) == 2


def test_attempting_to_overwrite_raises(tmp_path):
    lib_dir = tmp_path / "lib"
    objects_dir = lib_dir / "objects"
    objects_dir.mkdir(parents=True)
    image = tmp_path / "candidate.png"
    image.write_bytes(b"new-content")

    import hashlib

    result_id = hashlib.sha256(b"new-content").hexdigest()[:16]
    target = objects_dir / f"{result_id}.png"
    target.write_bytes(b"different-existing-content")

    with pytest.raises(AssertionError):
        add_result(lib_dir, image, {"task": "T8"})
