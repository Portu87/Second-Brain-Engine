from __future__ import annotations

from pathlib import Path

import yaml

from conftest import create_valid_project, write_yaml
from second_brain_engine.compiler import compile_project
from second_brain_engine.schema import schema_errors
from second_brain_engine.validator import validate_project


def codes(root: Path) -> set[str]:
    return {item.code for item in validate_project(root).errors}


def test_schema_formats_are_enforced() -> None:
    manifest = {
        "schema_version": "1.0",
        "project_id": "valid-project",
        "name": "Valid",
        "language": "en",
        "status": "active",
        "authority_model": "compiled-state",
        "confidentiality_default": "internal",
        "root_nodes": [],
        "created_at": "not-a-date",
    }
    messages = schema_errors("project", manifest)
    assert any("created_at" in message and "date-time" in message for message in messages)


def test_prohibited_source_is_blocking(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    record_path = root / "sources" / "records" / "SRC-EVIDENCE-001.yaml"
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    record["classification"] = "prohibited"
    write_yaml(record_path, record)

    assert "SECURITY.PROHIBITED_SOURCE" in codes(root)


def test_supersession_cycle_across_multiple_edges_is_reported(
    initialized_project: Path,
) -> None:
    root = create_valid_project(initialized_project)
    first_path = root / "decisions" / "DEC-RULE-001.yaml"
    first = yaml.safe_load(first_path.read_text(encoding="utf-8"))
    first["supersedes"] = ["DEC-RULE-002", "DEC-RULE-003"]
    write_yaml(first_path, first)

    second = {
        **first,
        "id": "DEC-RULE-002",
        "title": "Second",
        "status": "rejected",
        "decided_at": "2026-02-01T00:00:00Z",
        "effective_from": "2026-02-01T00:00:00Z",
        "supersedes": [],
    }
    third = {
        **first,
        "id": "DEC-RULE-003",
        "title": "Third",
        "status": "rejected",
        "decided_at": "2026-03-01T00:00:00Z",
        "effective_from": "2026-03-01T00:00:00Z",
        "supersedes": ["DEC-RULE-001"],
    }
    write_yaml(root / "decisions" / "DEC-RULE-002.yaml", second)
    write_yaml(root / "decisions" / "DEC-RULE-003.yaml", third)
    compile_project(root)

    assert "AUTH.SUPERSESSION_CYCLE" in codes(root)
