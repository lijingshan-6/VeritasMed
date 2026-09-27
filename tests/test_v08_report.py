"""A research table cannot count duplicates or stale cached scores as evidence."""
import importlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def saved_phase(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts/verification"))
    report = importlib.import_module("v08_r2_report")
    source = ROOT / "data/verification/v08/r2"
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf8"))
    cases = {c["id"]: c for c in manifest["cases"] + manifest["natural_cases"]}
    directory = tmp_path / "development"
    directory.mkdir()
    (directory / "protocol.json").write_bytes((source / "development/protocol.json").read_bytes())
    with (source / "development/predictions.jsonl").open(encoding="utf8") as stream:
        row = json.loads(next(stream))
    monkeypatch.setattr(report, "OUT", tmp_path)
    return report, directory / "predictions.jsonl", row, cases, report.object_hash(manifest)


def test_duplicate_is_not_a_missing_job(saved_phase):
    report, path, row, cases, sha = saved_phase
    path.write_text((json.dumps(row) + "\n") * 2, encoding="utf8")
    with pytest.raises(ValueError, match="duplicate or unscheduled"):
        report.phase_records("development", cases, sha)


def test_saved_scores_are_recomputed(saved_phase):
    report, path, row, cases, sha = saved_phase
    row["metrics"]["completed_answer"] = not row["metrics"]["completed_answer"]
    path.write_text(json.dumps(row) + "\n", encoding="utf8")
    with pytest.raises(ValueError, match="cached metrics differ"):
        report.phase_records("development", cases, sha)


def test_partial_phase_retains_planned_denominator(saved_phase):
    report, path, row, cases, sha = saved_phase
    path.write_text(json.dumps(row) + "\n", encoding="utf8")
    records, planned = report.phase_records("development", cases, sha)
    assert len(records) == 1
    assert planned == 144
