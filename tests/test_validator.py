from __future__ import annotations

import json
from pathlib import Path

import yaml

from conftest import create_valid_project, write_yaml
from second_brain_engine.compiler import compile_project
from second_brain_engine.project import ingest_source
from second_brain_engine.validator import validate_project


def codes(root: Path) -> set[str]:
    return {item.code for item in validate_project(root).errors}


def test_valid_compiled_project_passes(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    assert validate_project(root).as_dict()["ok"] is True


def test_tampered_or_stale_snapshot_fails(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    snapshot_path = root / "canon" / "snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["rules"][0]["value"] = 999
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    assert "AUTH.SNAPSHOT_STALE_OR_TAMPERED" in codes(root)


def test_missing_decision_source_is_reported(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    decision_path = root / "decisions" / "DEC-RULE-001.yaml"
    decision = yaml.safe_load(decision_path.read_text(encoding="utf-8"))
    decision["source_ids"] = ["SRC-MISSING-001"]
    write_yaml(decision_path, decision)
    compile_project(root)

    assert "TRACE.DECISION_SOURCE_MISSING" in codes(root)


def test_active_rule_collision_is_reported(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    second = {
        "schema_version": "1.0",
        "id": "DEC-RULE-002",
        "project_id": "example-project",
        "title": "Conflicting target",
        "status": "approved",
        "decided_at": "2026-02-01T00:00:00Z",
        "effective_from": "2026-02-01T00:00:00Z",
        "approved_by": "owner",
        "source_ids": ["SRC-EVIDENCE-001"],
        "rationale": "Intentional collision fixture.",
        "operations": [
            {
                "op": "upsert_rule",
                "rule": {
                    "rule_id": "operations.support.alternate-target",
                    "entity": "support",
                    "field": "response_target_hours",
                    "value": 48,
                    "scope": "global",
                },
            }
        ],
        "supersedes": [],
        "links": [],
    }
    write_yaml(root / "decisions" / "DEC-RULE-002.yaml", second)
    compile_project(root)

    assert "AUTH.ACTIVE_RULE_COLLISION" in codes(root)


def test_disconnected_graph_and_missing_reference_are_reported(
    initialized_project: Path, tmp_path: Path
) -> None:
    root = create_valid_project(initialized_project)
    extra = tmp_path / "extra.txt"
    extra.write_text("extra", encoding="utf-8")
    ingest_source(root, extra, "SRC-EXTRA-001", title="Extra", origin="Fixture")
    assert "GRAPH.DISCONNECTED" in codes(root)

    record_path = root / "sources" / "records" / "SRC-EXTRA-001.yaml"
    record = yaml.safe_load(record_path.read_text(encoding="utf-8"))
    record["links"] = ["SRC-NOT-THERE-001"]
    write_yaml(record_path, record)
    result = codes(root)
    assert "GRAPH.REFERENCE_MISSING" in result
    assert "GRAPH.DISCONNECTED" in result


def test_duplicate_ids_and_project_mismatch_are_reported(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    duplicate = {
        "schema_version": "1.0",
        "id": "DEC-RULE-001",
        "project_id": "other-project",
        "title": "Duplicate",
        "status": "rejected",
        "decided_at": "2026-03-01T00:00:00Z",
        "effective_from": "2026-03-01T00:00:00Z",
        "approved_by": "owner",
        "source_ids": ["SRC-EVIDENCE-001"],
        "rationale": "Fixture",
        "operations": [
            {
                "op": "upsert_rule",
                "rule": {
                    "rule_id": "duplicate.rule",
                    "entity": "x",
                    "field": "y",
                    "value": 1,
                    "scope": "global",
                },
            }
        ],
        "supersedes": [],
        "links": [],
    }
    write_yaml(root / "decisions" / "duplicate.yaml", duplicate)
    result = codes(root)
    assert "STRUCTURE.DUPLICATE_ID" in result
    assert "STRUCTURE.PROJECT_ID_MISMATCH" in result


def test_possible_secret_is_blocking(initialized_project: Path) -> None:
    root = initialized_project
    (root / "knowledge" / "oops.txt").write_text(
        "api_key=ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890", encoding="utf-8"
    )
    assert "SECURITY.POSSIBLE_SECRET" in codes(root)


def test_invalid_yaml_and_missing_manifest_are_reported(tmp_path: Path) -> None:
    root = tmp_path / "missing"
    root.mkdir()
    assert "STRUCTURE.MANIFEST_MISSING" in codes(root)

    project = tmp_path / "invalid"
    project.mkdir()
    (project / "project.yaml").write_text("not: [valid", encoding="utf-8")
    assert "STRUCTURE.YAML_INVALID" in codes(project)


def test_approved_decision_without_snapshot_is_reported(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    (root / "canon" / "snapshot.json").unlink()
    assert "AUTH.SNAPSHOT_MISSING" in codes(root)


def test_missing_raw_file_and_output_references_are_reported(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    source_record_path = root / "sources" / "records" / "SRC-EVIDENCE-001.yaml"
    source = yaml.safe_load(source_record_path.read_text(encoding="utf-8"))
    (root / source["path"]).unlink()

    output = {
        "schema_version": "1.0",
        "id": "OUT-REPORT-001",
        "project_id": "example-project",
        "title": "Report",
        "created_at": "2026-01-02T00:00:00Z",
        "generator": "fixture",
        "canon_sha256": "a" * 64,
        "source_ids": ["SRC-MISSING-001"],
        "decision_ids": ["DEC-MISSING-001"],
        "artifact_path": "artifacts/report.md",
        "status": "draft",
        "links": ["DEC-RULE-001"],
    }
    write_yaml(root / "outputs" / "OUT-REPORT-001.yaml", output)
    result = codes(root)
    assert "SOURCE.RAW_MISSING" in result
    assert "TRACE.OUTPUT_SOURCE_MISSING" in result
    assert "TRACE.OUTPUT_DECISION_MISSING" in result


def test_supersession_cycle_is_reported(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    first_path = root / "decisions" / "DEC-RULE-001.yaml"
    first = yaml.safe_load(first_path.read_text(encoding="utf-8"))
    first["supersedes"] = ["DEC-RULE-002"]
    write_yaml(first_path, first)

    second = {
        **first,
        "id": "DEC-RULE-002",
        "title": "Second",
        "decided_at": "2026-02-01T00:00:00Z",
        "effective_from": "2026-02-01T00:00:00Z",
        "supersedes": ["DEC-RULE-001"],
    }
    write_yaml(root / "decisions" / "DEC-RULE-002.yaml", second)
    compile_project(root)
    assert "AUTH.SUPERSESSION_CYCLE" in codes(root)


def test_snapshot_invalid_json_is_reported(initialized_project: Path) -> None:
    root = create_valid_project(initialized_project)
    (root / "canon" / "snapshot.json").write_text("{bad", encoding="utf-8")
    assert "AUTH.SNAPSHOT_INVALID" in codes(root)
