from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image


MODULE_PATH = Path(__file__).resolve().parents[1] / "run_assisted_batch.py"
SPEC = importlib.util.spec_from_file_location("run_assisted_batch", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
batch = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = batch
SPEC.loader.exec_module(batch)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_source(path: Path, size=(4, 4), color=(220, 230, 240)) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def write_proposal(path: Path, size=(4, 4), mode="L") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if mode == "RGBA":
        image = Image.new("RGBA", size, (12, 34, 56, 0))
        alpha = Image.new("L", size, 128)
        image.putalpha(alpha)
    else:
        image = Image.new(mode, size, 128)
    image.save(path)
    return path


def write_corrections(path: Path, size=(4, 4), mode="RGBA") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    color = (0, 0, 0, 0) if mode == "RGBA" else (0, 0, 0)
    Image.new(mode, size, color).save(path)
    return path


def case_payload(
    case_id: str,
    source: Path,
    proposal: Path,
    output_dir: Path,
    *,
    legacy=False,
    corrections: Path | None = None,
) -> dict:
    with Image.open(source) as source_image:
        source_size = source_image.size
    payload = {
        "id": case_id,
        "source": {
            "path": str(source),
            "sha256": sha256(source),
            "size_wh": list(source_size),
        },
        "output_dir": str(output_dir),
    }
    if legacy:
        payload["legacy_rgba_proposal"] = {"path": str(proposal), "resample": "lanczos"}
    else:
        payload["proposal"] = {"path": str(proposal)}
    if corrections is not None:
        payload["corrections"] = {"path": str(corrections)}
    return payload


def write_spec(path: Path, cases: list[dict]) -> Path:
    path.write_text(
        json.dumps({"schema": batch.SCHEMA, "cases": cases}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def write_core(path: Path) -> Path:
    path.write_text("# fake assisted core\n", encoding="utf-8")
    return path


class FakeCore:
    def __init__(self):
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str]):
        self.commands.append(command)

        def value(flag: str) -> Path:
            return Path(command[command.index(flag) + 1])

        with Image.open(value("--source")) as source:
            size = source.size
        with Image.open(value("--proposal")) as proposal:
            assert proposal.mode == "L"
            assert proposal.size == size
        candidate = value("--output")
        metrics = value("--metrics")
        manifest = value("--manifest")
        review = value("--review-board")
        for path in (candidate, metrics, manifest, review):
            path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", size, (40, 80, 120, 128)).save(candidate)
        metrics.write_text(json.dumps({"schema": "fake-metrics/v1"}) + "\n", encoding="utf-8")
        manifest.write_text(
            json.dumps({"status": "candidate-unapproved", "production_ready": False}) + "\n",
            encoding="utf-8",
        )
        Image.new("RGB", size, (255, 0, 255)).save(review)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")


def execute(
    spec: Path,
    aggregate: Path,
    core: Path,
    fake: FakeCore,
    **changes,
):
    options = {
        "core_path": core,
        "backend": "vitmatte",
        "device": "mps",
        "correction_unlock_radius": 110,
        "command_runner": fake,
    }
    options.update(changes)
    return batch.execute_batch(spec, aggregate, **options)


def test_legacy_rgba_is_normalized_and_command_is_fully_explicit_then_resumes(tmp_path):
    source = write_source(tmp_path / "inputs" / "image14.png")
    proposal = write_proposal(tmp_path / "inputs" / "image14-x2.png", size=(8, 8), mode="RGBA")
    corrections = write_corrections(tmp_path / "inputs" / "image14-corrections.png")
    output_dir = tmp_path / "Images" / "candidates" / "image14"
    spec = write_spec(
        tmp_path / "batch.json",
        [case_payload("image14", source, proposal, output_dir, legacy=True, corrections=corrections)],
    )
    aggregate = tmp_path / "batch-report.json"
    core = write_core(tmp_path / "fake_core.py")
    fake = FakeCore()

    report = execute(spec, aggregate, core, fake)

    assert report["status"] == "success"
    assert report["cases"][0]["action"] == "ran"
    assert report["cases"][0]["source_unchanged_proof"]["unchanged"] is True
    assert len(fake.commands) == 1
    command = fake.commands[0]
    assert command[:2] == [sys.executable, str(core.resolve())]
    assert command[command.index("--source") + 1] == str(source.resolve())
    assert command[command.index("--proposal") + 1] == str(output_dir / "native-proposal.png")
    assert command[command.index("--corrections") + 1] == str(corrections.resolve())
    assert command[command.index("--backend") + 1] == "vitmatte"
    assert command[command.index("--device") + 1] == "mps"
    assert command[command.index("--correction-unlock-radius") + 1] == "110"
    assert "--overwrite" not in command
    with Image.open(output_dir / "native-proposal.png") as native:
        assert native.mode == "L"
        assert native.size == (4, 4)
    state = json.loads((output_dir / "batch-manifest.json").read_text(encoding="utf-8"))
    assert state["inputs"]["proposal_native"]["sha256"] == sha256(
        output_dir / "native-proposal.png"
    )
    assert state["production_ready"] is False
    assert state["promotion_performed"] is False

    resumed = execute(spec, aggregate, core, fake)
    assert resumed["cases"][0]["action"] == "resumed"
    assert len(fake.commands) == 1


def test_resume_config_mismatch_fails_without_invoking_core(tmp_path):
    source = write_source(tmp_path / "inputs" / "source.png")
    proposal = write_proposal(tmp_path / "inputs" / "proposal.png")
    output_dir = tmp_path / "candidates" / "one"
    spec = write_spec(
        tmp_path / "batch.json", [case_payload("one", source, proposal, output_dir)]
    )
    core = write_core(tmp_path / "fake_core.py")
    fake = FakeCore()
    execute(spec, tmp_path / "report-1.json", core, fake)

    report = execute(
        spec,
        tmp_path / "report-2.json",
        core,
        fake,
        correction_unlock_radius=111,
    )

    assert report["status"] == "partial-failure"
    assert report["cases"][0]["status"] == "failure"
    assert "resume mismatch: fingerprint changed" in report["cases"][0]["error"]
    assert "pass --overwrite" in report["cases"][0]["error"]
    assert len(fake.commands) == 1


def test_final_output_directory_is_rejected_before_execution(tmp_path):
    source = write_source(tmp_path / "inputs" / "source.png")
    proposal = write_proposal(tmp_path / "inputs" / "proposal.png")
    spec = write_spec(
        tmp_path / "batch.json",
        [case_payload("one", source, proposal, tmp_path / "Images" / "finals" / "one")],
    )
    core = write_core(tmp_path / "fake_core.py")

    with pytest.raises(batch.BatchError, match="refuses final-path promotion"):
        execute(spec, tmp_path / "report.json", core, FakeCore())


@pytest.mark.parametrize(
    ("bad_kind", "expected"),
    [
        ("proposal-size", "native proposal dimensions must match source"),
        ("correction-mode", "corrections must be genuine RGBA"),
        ("correction-size", "corrections dimensions must exactly match source"),
    ],
)
def test_native_dimensions_and_genuine_correction_exactness_are_enforced(
    tmp_path, bad_kind, expected
):
    source = write_source(tmp_path / "inputs" / "source.png")
    proposal_size = (5, 4) if bad_kind == "proposal-size" else (4, 4)
    proposal = write_proposal(tmp_path / "inputs" / "proposal.png", size=proposal_size)
    corrections = None
    if bad_kind == "correction-mode":
        corrections = write_corrections(tmp_path / "inputs" / "corrections.png", mode="RGB")
    elif bad_kind == "correction-size":
        corrections = write_corrections(tmp_path / "inputs" / "corrections.png", size=(4, 5))
    spec = write_spec(
        tmp_path / "batch.json",
        [
            case_payload(
                "one",
                source,
                proposal,
                tmp_path / "candidates" / "one",
                corrections=corrections,
            )
        ],
    )
    core = write_core(tmp_path / "fake_core.py")

    report = execute(spec, tmp_path / "report.json", core, FakeCore())

    assert report["cases"][0]["status"] == "failure"
    assert expected in report["cases"][0]["error"]


def test_dry_run_is_deterministic_write_free_and_case_filter_is_exact(tmp_path):
    cases = []
    for case_id in ("one", "two"):
        source = write_source(tmp_path / "inputs" / f"{case_id}-source.png")
        proposal = write_proposal(tmp_path / "inputs" / f"{case_id}-proposal.png")
        cases.append(
            case_payload(case_id, source, proposal, tmp_path / "candidates" / case_id)
        )
    spec = write_spec(tmp_path / "batch.json", cases)
    aggregate = tmp_path / "report.json"
    core = write_core(tmp_path / "fake_core.py")
    fake = FakeCore()

    first = execute(
        spec,
        aggregate,
        core,
        fake,
        case_filter=["two"],
        dry_run=True,
    )
    second = execute(
        spec,
        aggregate,
        core,
        fake,
        case_filter=["two"],
        dry_run=True,
    )

    assert first == second
    assert [item["id"] for item in first["cases"]] == ["two"]
    assert first["cases"][0]["status"] == "planned"
    assert first["cases"][0]["command"][0] == sys.executable
    assert not aggregate.exists()
    assert not (tmp_path / "candidates").exists()
    assert fake.commands == []

    with pytest.raises(batch.BatchError, match="unknown case ids"):
        execute(
            spec,
            aggregate,
            core,
            fake,
            case_filter=["missing"],
            dry_run=True,
        )


def test_duplicate_input_paths_are_rejected_globally(tmp_path):
    source = write_source(tmp_path / "inputs" / "shared-source.png")
    proposal_one = write_proposal(tmp_path / "inputs" / "proposal-one.png")
    proposal_two = write_proposal(tmp_path / "inputs" / "proposal-two.png")
    spec = write_spec(
        tmp_path / "batch.json",
        [
            case_payload("one", source, proposal_one, tmp_path / "candidates" / "one"),
            case_payload("two", source, proposal_two, tmp_path / "candidates" / "two"),
        ],
    )
    core = write_core(tmp_path / "fake_core.py")

    with pytest.raises(batch.BatchError, match="duplicate input path"):
        execute(spec, tmp_path / "report.json", core, FakeCore(), dry_run=True)


def test_aggregate_path_cannot_collide_with_an_input(tmp_path):
    source = write_source(tmp_path / "inputs" / "source.png")
    proposal = write_proposal(tmp_path / "inputs" / "proposal.png")
    spec = write_spec(
        tmp_path / "batch.json",
        [case_payload("one", source, proposal, tmp_path / "candidates" / "one")],
    )
    core = write_core(tmp_path / "fake_core.py")

    with pytest.raises(batch.BatchError, match="aggregate report path collides"):
        execute(spec, source, core, FakeCore(), dry_run=True)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("sha256", "0" * 64, "source SHA-256 mismatch"),
        ("size_wh", [5, 4], "source dimensions mismatch"),
    ],
)
def test_declared_source_hash_and_dimensions_are_verified(tmp_path, field, value, expected):
    source = write_source(tmp_path / "inputs" / "source.png")
    proposal = write_proposal(tmp_path / "inputs" / "proposal.png")
    case = case_payload("one", source, proposal, tmp_path / "candidates" / "one")
    case["source"][field] = value
    spec = write_spec(tmp_path / "batch.json", [case])
    core = write_core(tmp_path / "fake_core.py")

    report = execute(spec, tmp_path / "report.json", core, FakeCore())

    assert report["cases"][0]["status"] == "failure"
    assert expected in report["cases"][0]["error"]
