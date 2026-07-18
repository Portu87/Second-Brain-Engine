"""Deterministic compiler from approved decisions to canonical state."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import CompilationError, ProjectError
from .io import atomic_write_json, iter_yaml_files, load_yaml


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _decision_sort_key(decision: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(decision.get("effective_from", "")),
        str(decision.get("decided_at", "")),
        str(decision.get("id", "")),
    )


def load_decisions(project_root: Path) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for path in iter_yaml_files(project_root / "decisions"):
        if path.name == ".gitkeep":
            continue
        decision = load_yaml(path)
        decision["_path"] = path.relative_to(project_root).as_posix()
        decisions.append(decision)
    return decisions


def build_snapshot(project_root: Path) -> dict[str, Any]:
    """Compile approved decisions into an in-memory canonical snapshot."""
    project = load_yaml(project_root / "project.yaml")
    project_id = project.get("project_id")
    if not isinstance(project_id, str):
        raise CompilationError("Project manifest has no project_id")

    approved = sorted(
        (item for item in load_decisions(project_root) if item.get("status") == "approved"),
        key=_decision_sort_key,
    )
    rules: dict[str, dict[str, Any]] = {}
    applied: list[str] = []

    for decision in approved:
        decision_id = decision.get("id")
        if not isinstance(decision_id, str):
            raise CompilationError(f"Decision without valid id: {decision.get('_path')}")
        operations = decision.get("operations")
        if not isinstance(operations, list):
            raise CompilationError(f"Decision {decision_id} has no operations list")
        for index, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise CompilationError(f"Decision {decision_id} operation {index} is not an object")
            op_name = operation.get("op")
            if op_name == "upsert_rule":
                raw_rule = operation.get("rule")
                if not isinstance(raw_rule, dict):
                    raise CompilationError(f"Decision {decision_id} has invalid upsert_rule")
                rule_id = raw_rule.get("rule_id")
                if not isinstance(rule_id, str):
                    raise CompilationError(f"Decision {decision_id} has rule without rule_id")
                prior = rules.get(rule_id)
                revision = int(prior.get("revision", 0)) + 1 if prior else 1
                rule = dict(raw_rule)
                rule.update(
                    {
                        "rule_id": rule_id,
                        "project_id": project_id,
                        "status": raw_rule.get("status", "active"),
                        "decision_id": decision_id,
                        "source_ids": list(decision.get("source_ids", [])),
                        "effective_from": raw_rule.get(
                            "effective_from", decision.get("effective_from")
                        ),
                        "revision": revision,
                    }
                )
                rules[rule_id] = rule
            elif op_name == "deactivate_rule":
                rule_id = operation.get("rule_id")
                if not isinstance(rule_id, str) or rule_id not in rules:
                    raise CompilationError(
                        f"Decision {decision_id} deactivates missing rule {rule_id!r}"
                    )
                rules[rule_id] = {
                    **rules[rule_id],
                    "status": "inactive",
                    "decision_id": decision_id,
                    "source_ids": list(decision.get("source_ids", [])),
                    "revision": int(rules[rule_id].get("revision", 0)) + 1,
                }
            else:
                raise CompilationError(f"Decision {decision_id} has unsupported op {op_name!r}")
        applied.append(decision_id)

    semantic = {
        "schema_version": "1.0",
        "project_id": project_id,
        "authority_model": "compiled-state",
        "decision_ids": applied,
        "rules": [rules[key] for key in sorted(rules)],
    }
    canonical = json.dumps(semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    semantic["content_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return semantic


def compile_project(project_root: Path) -> Path:
    """Compile and atomically persist the canonical snapshot."""
    if not (project_root / "project.yaml").is_file():
        raise ProjectError(f"Not an initialized project: {project_root}")
    snapshot = build_snapshot(project_root)
    snapshot["generated_at"] = _now()
    output = project_root / "canon" / "snapshot.json"
    atomic_write_json(output, snapshot)
    return output
