from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from second_brain_engine.errors import ProjectError
from second_brain_engine.project import ingest_source, init_project
from second_brain_engine.validator import validate_project


def test_init_project_creates_empty_valid_layout(tmp_path: Path) -> None:
    root = init_project(tmp_path / "brain", "alpha-project", "Alpha")

    assert (root / "project.yaml").is_file()
    assert (root / "sources/raw").is_dir()
    assert (root / "decisions").is_dir()
    assert validate_project(root).ok


def test_init_rejects_invalid_id_and_nonempty_directory(tmp_path: Path) -> None:
    with pytest.raises(ProjectError, match="project_id"):
        init_project(tmp_path / "bad", "INVALID", "Bad")

    target = tmp_path / "existing"
    target.mkdir()
    (target / "file.txt").write_text("data", encoding="utf-8")
    with pytest.raises(ProjectError, match="non-empty"):
        init_project(target, "valid-project", "Valid")


def test_ingest_registers_digest_and_detects_mutation(
    initialized_project: Path, tmp_path: Path
) -> None:
    source = tmp_path / "note.txt"
    source.write_text("original\n", encoding="utf-8")
    record_path = ingest_source(
        initialized_project,
        source,
        "SRC-NOTE-001",
        title="Note",
        origin="Test",
    )
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))

    assert len(record["sha256"]) == 64
    assert validate_project(initialized_project).ok is False  # records require a graph root

    manifest_path = initialized_project / "project.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["root_nodes"] = ["SRC-NOTE-001"]
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    assert validate_project(initialized_project).ok

    raw = initialized_project / record["path"]
    raw.write_text("changed\n", encoding="utf-8")
    report = validate_project(initialized_project)
    assert "SOURCE.IMMUTABILITY_VIOLATION" in {item.code for item in report.errors}


def test_ingest_rejects_duplicate_invalid_and_missing_sources(
    initialized_project: Path, tmp_path: Path
) -> None:
    source = tmp_path / "note.txt"
    source.write_text("x", encoding="utf-8")
    ingest_source(initialized_project, source, "SRC-NOTE-001", title="Note", origin="Test")

    with pytest.raises(ProjectError, match="already exists"):
        ingest_source(initialized_project, source, "SRC-NOTE-001", title="Note", origin="Test")
    with pytest.raises(ProjectError, match="source_id"):
        ingest_source(initialized_project, source, "bad", title="Note", origin="Test")
    with pytest.raises(ProjectError, match="regular file"):
        ingest_source(
            initialized_project,
            tmp_path / "missing.txt",
            "SRC-MISSING-001",
            title="Missing",
            origin="Test",
        )


def test_ingest_requires_initialized_project(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("x", encoding="utf-8")
    with pytest.raises(ProjectError, match="initialized project"):
        ingest_source(
            tmp_path / "not-a-project",
            source,
            "SRC-VALID-001",
            title="Source",
            origin="Test",
        )
