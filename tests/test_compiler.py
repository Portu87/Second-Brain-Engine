from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import create_valid_project, write_yaml
from second_brain_engine.compiler import build_snapshot, compile_project
from second_brain_engine.errors import CompilationError


def test_compile_is_deterministic_and_tracks_provenance(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    first = build_snapshot(root)
    second = build_snapshot(root)

    assert first == second
    assert first["decision_ids"] == ["DEC-RULE-001"]
    rule = first["rules"][0]
    assert rule["decision_id"] == "DEC-RULE-001"
    assert rule["source_ids"] == ["SRC-EVIDENCE-001"]
    assert rule["revision"] == 1

    path = compile_project(root)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["content_sha256"] == first["content_sha256"]
    assert "generated_at" in persisted


def test_later_decision_updates_then_deactivates_rule(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    source_ids = ["SRC-EVIDENCE-001"]
    update = {
        "schema_version": "1.0",
        "id": "DEC-RULE-002",
        "project_id": "example-project",
        "title": "Update and deactivate target",
        "status": "approved",
        "decided_at": "2026-02-01T00:00:00Z",
        "effective_from": "2026-02-01T00:00:00Z",
        "approved_by": "owner",
        "source_ids": source_ids,
        "rationale": "Updated evidence changes the target.",
        "operations": [
            {
                "op": "upsert_rule",
                "rule": {
                    "rule_id": "operations.support.response-target",
                    "entity": "support",
                    "field": "response_target_hours",
                    "value": 12,
                    "scope": "global",
                },
            },
            {"op": "deactivate_rule", "rule_id": "operations.support.response-target"},
        ],
        "supersedes": ["DEC-RULE-001"],
        "links": [],
    }
    write_yaml(root / "decisions" / "DEC-RULE-002.yaml", update)
    snapshot = build_snapshot(root)

    assert snapshot["decision_ids"] == ["DEC-RULE-001", "DEC-RULE-002"]
    assert snapshot["rules"][0]["value"] == 12
    assert snapshot["rules"][0]["status"] == "inactive"
    assert snapshot["rules"][0]["revision"] == 3


def test_compiler_rejects_missing_rule_and_unknown_operation(initialized_project: Path) -> None:
    decision_base = {
        "schema_version": "1.0",
        "id": "DEC-BAD-001",
        "project_id": "example-project",
        "title": "Bad",
        "status": "approved",
        "decided_at": "2026-01-01T00:00:00Z",
        "effective_from": "2026-01-01T00:00:00Z",
        "approved_by": "owner",
        "source_ids": ["SRC-NOT-USED-001"],
        "rationale": "Test",
        "supersedes": [],
        "links": [],
    }
    write_yaml(
        initialized_project / "decisions" / "bad.yaml",
        {**decision_base, "operations": [{"op": "deactivate_rule", "rule_id": "missing.rule"}]},
    )
    with pytest.raises(CompilationError, match="deactivates missing rule"):
        build_snapshot(initialized_project)

    (initialized_project / "decisions" / "bad.yaml").unlink()
    write_yaml(
        initialized_project / "decisions" / "bad.yaml",
        {**decision_base, "operations": [{"op": "unknown"}]},
    )
    with pytest.raises(CompilationError, match="unsupported op"):
        build_snapshot(initialized_project)


def test_compiler_rejects_non_mapping_operation_and_rule_without_id(
    initialized_project: Path,
) -> None:
    base = {
        "schema_version": "1.0",
        "id": "DEC-BAD-002",
        "project_id": "example-project",
        "title": "Bad operation",
        "status": "approved",
        "decided_at": "2026-01-01T00:00:00Z",
        "effective_from": "2026-01-01T00:00:00Z",
        "approved_by": "owner",
        "source_ids": ["SRC-PLACEHOLDER-001"],
        "rationale": "Fixture",
        "supersedes": [],
        "links": [],
    }
    write_yaml(initialized_project / "decisions" / "bad.yaml", {**base, "operations": ["bad"]})
    with pytest.raises(CompilationError, match="not an object"):
        build_snapshot(initialized_project)

    write_yaml(
        initialized_project / "decisions" / "bad.yaml",
        {**base, "operations": [{"op": "upsert_rule", "rule": {"entity": "x"}}]},
    )
    with pytest.raises(CompilationError, match="rule without rule_id"):
        build_snapshot(initialized_project)
