from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from second_brain_engine.compiler import compile_project
from second_brain_engine.project import ingest_source, init_project


@pytest.fixture
def initialized_project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    init_project(root, "example-project", "Example Project")
    return root


def write_yaml(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def create_valid_project(root: Path) -> Path:
    source_input = root.parent / "evidence.txt"
    source_input.write_text("accepted target: 24 hours\n", encoding="utf-8")
    ingest_source(
        root,
        source_input,
        "SRC-EVIDENCE-001",
        title="Primary evidence",
        origin="Fixture",
    )
    decision = {
        "schema_version": "1.0",
        "id": "DEC-RULE-001",
        "project_id": "example-project",
        "title": "Define target",
        "status": "approved",
        "decided_at": "2026-01-01T00:00:00Z",
        "effective_from": "2026-01-01T00:00:00Z",
        "approved_by": "owner",
        "source_ids": ["SRC-EVIDENCE-001"],
        "rationale": "The source establishes the target.",
        "operations": [
            {
                "op": "upsert_rule",
                "rule": {
                    "rule_id": "operations.support.response-target",
                    "entity": "support",
                    "field": "response_target_hours",
                    "value": 24,
                    "scope": "global",
                },
            }
        ],
        "supersedes": [],
        "links": [],
    }
    write_yaml(root / "decisions" / "DEC-RULE-001.yaml", decision)
    manifest_path = root / "project.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["root_nodes"] = ["DEC-RULE-001"]
    write_yaml(manifest_path, manifest)
    compile_project(root)
    return root
