"""Layered validation for project integrity, authority, traceability, and graph health."""

from __future__ import annotations

import re
from collections import defaultdict, deque
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .compiler import build_snapshot
from .errors import CompilationError, ProjectError
from .io import iter_yaml_files, load_json, load_yaml, sha256_file
from .models import Finding, ValidationReport
from .schema import schema_errors

SECRET_PATTERNS = {
    "generic-api-key": re.compile(
        r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}"
    ),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
}

RECORD_DIRECTORIES = {
    "source": "sources/records",
    "decision": "decisions",
    "output": "outputs",
    "pending": "pending",
}


def _finding(
    code: str,
    message: str,
    path: Path | str | None = None,
    severity: str = "error",
) -> Finding:
    return Finding(
        code=code,
        severity=severity,  # type: ignore[arg-type]
        message=message,
        path=str(path) if path else None,
    )


def _load_records(project_root: Path, kind: str) -> tuple[list[dict[str, Any]], list[Finding]]:
    records: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for path in iter_yaml_files(project_root / RECORD_DIRECTORIES[kind]):
        try:
            record = load_yaml(path)
        except ProjectError as exc:
            findings.append(_finding("STRUCTURE.YAML_INVALID", str(exc), path))
            continue
        for message in schema_errors(kind, record):
            findings.append(_finding("STRUCTURE.SCHEMA", message, path))
        record["_path"] = path.relative_to(project_root).as_posix()
        records.append(record)
    return records, findings


def _validate_manifest(project_root: Path) -> tuple[dict[str, Any] | None, list[Finding]]:
    path = project_root / "project.yaml"
    if not path.is_file():
        return None, [_finding("STRUCTURE.MANIFEST_MISSING", "project.yaml is missing", path)]
    try:
        manifest = load_yaml(path)
    except ProjectError as exc:
        return None, [_finding("STRUCTURE.YAML_INVALID", str(exc), path)]
    return manifest, [
        _finding("STRUCTURE.SCHEMA", msg, path) for msg in schema_errors("project", manifest)
    ]


def _validate_unique_ids(records: Iterable[dict[str, Any]]) -> list[Finding]:
    by_id: dict[str, list[str]] = defaultdict(list)
    for record in records:
        record_id = record.get("id")
        if isinstance(record_id, str):
            by_id[record_id].append(str(record.get("_path", "unknown")))
    return [
        _finding("STRUCTURE.DUPLICATE_ID", f"ID {record_id} occurs in: {', '.join(paths)}")
        for record_id, paths in by_id.items()
        if len(paths) > 1
    ]


def _validate_project_ids(project_id: str, records: Iterable[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for record in records:
        if record.get("project_id") != project_id:
            findings.append(
                _finding(
                    "STRUCTURE.PROJECT_ID_MISMATCH",
                    f"Expected project_id {project_id!r}, got {record.get('project_id')!r}",
                    str(record.get("_path")),
                )
            )
    return findings


def _validate_sources(project_root: Path, sources: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    seen_paths: dict[str, str] = {}
    for source in sources:
        path_value = source.get("path")
        source_id = str(source.get("id", "unknown"))
        record_path = str(source.get("_path", "unknown"))
        if not isinstance(path_value, str):
            continue
        if path_value.startswith("/") or ".." in Path(path_value).parts:
            findings.append(
                _finding("SOURCE.UNSAFE_PATH", f"Unsafe source path: {path_value}", record_path)
            )
            continue
        raw_path = project_root / path_value
        if not raw_path.is_file():
            findings.append(
                _finding(
                    "SOURCE.RAW_MISSING",
                    f"Raw source is missing: {path_value}",
                    record_path,
                )
            )
            continue
        try:
            digest = sha256_file(raw_path)
        except ProjectError as exc:
            findings.append(_finding("SOURCE.RAW_INVALID", str(exc), record_path))
            continue
        if digest != source.get("sha256"):
            findings.append(
                _finding(
                    "SOURCE.IMMUTABILITY_VIOLATION",
                    f"Checksum mismatch for {source_id}; raw sources are append-only",
                    path_value,
                )
            )
        if raw_path.stat().st_size != source.get("size_bytes"):
            findings.append(
                _finding("SOURCE.SIZE_MISMATCH", f"Size mismatch for {source_id}", path_value)
            )
        if path_value in seen_paths:
            findings.append(
                _finding(
                    "SOURCE.PATH_REUSED",
                    f"Raw path is shared by {seen_paths[path_value]} and {source_id}",
                    path_value,
                )
            )
        seen_paths[path_value] = source_id
    return findings


def _validate_traceability(
    sources: list[dict[str, Any]], decisions: list[dict[str, Any]], outputs: list[dict[str, Any]]
) -> list[Finding]:
    findings: list[Finding] = []
    source_ids = {item.get("id") for item in sources}
    decision_ids = {item.get("id") for item in decisions}
    for decision in decisions:
        for source_id in decision.get("source_ids", []):
            if source_id not in source_ids:
                findings.append(
                    _finding(
                        "TRACE.DECISION_SOURCE_MISSING",
                        f"Decision {decision.get('id')} references missing source {source_id}",
                        str(decision.get("_path")),
                    )
                )
    for output in outputs:
        for source_id in output.get("source_ids", []):
            if source_id not in source_ids:
                findings.append(
                    _finding(
                        "TRACE.OUTPUT_SOURCE_MISSING",
                        f"Output {output.get('id')} references missing source {source_id}",
                        str(output.get("_path")),
                    )
                )
        for decision_id in output.get("decision_ids", []):
            if decision_id not in decision_ids:
                findings.append(
                    _finding(
                        "TRACE.OUTPUT_DECISION_MISSING",
                        f"Output {output.get('id')} references missing decision {decision_id}",
                        str(output.get("_path")),
                    )
                )
    return findings


def _validate_authority(project_root: Path, decisions: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    approved_ids = {item.get("id") for item in decisions if item.get("status") == "approved"}
    supersedes: dict[str, str] = {}
    for decision in decisions:
        superseded = decision.get("supersedes", [])
        for prior in superseded:
            if prior not in approved_ids and prior not in {item.get("id") for item in decisions}:
                findings.append(
                    _finding(
                        "AUTH.SUPERSEDED_DECISION_MISSING",
                        f"Decision {decision.get('id')} supersedes missing decision {prior}",
                        str(decision.get("_path")),
                    )
                )
            supersedes[str(decision.get("id"))] = str(prior)

    for start in supersedes:
        seen: set[str] = set()
        current = start
        while current in supersedes:
            if current in seen:
                findings.append(
                    _finding(
                        "AUTH.SUPERSESSION_CYCLE",
                        f"Decision supersession cycle at {current}",
                    )
                )
                break
            seen.add(current)
            current = supersedes[current]

    try:
        expected = build_snapshot(project_root)
    except (CompilationError, ProjectError) as exc:
        findings.append(_finding("AUTH.COMPILATION_FAILED", str(exc)))
        return findings

    snapshot_path = project_root / "canon" / "snapshot.json"
    if not snapshot_path.is_file():
        if approved_ids:
            findings.append(
                _finding(
                    "AUTH.SNAPSHOT_MISSING",
                    "Approved decisions exist but canon/snapshot.json has not been compiled",
                    snapshot_path,
                )
            )
        return findings
    try:
        actual = load_json(snapshot_path)
    except ProjectError as exc:
        findings.append(_finding("AUTH.SNAPSHOT_INVALID", str(exc), snapshot_path))
        return findings
    for message in schema_errors("snapshot", actual):
        findings.append(_finding("STRUCTURE.SCHEMA", message, snapshot_path))

    semantic_keys = (
        "schema_version",
        "project_id",
        "authority_model",
        "decision_ids",
        "rules",
        "content_sha256",
    )
    if any(actual.get(key) != expected.get(key) for key in semantic_keys):
        findings.append(
            _finding(
                "AUTH.SNAPSHOT_STALE_OR_TAMPERED",
                "Canonical snapshot does not match deterministic compilation of approved decisions",
                snapshot_path,
            )
        )

    active_keys: dict[tuple[str, str, str], str] = {}
    for rule in actual.get("rules", []):
        if not isinstance(rule, dict) or rule.get("status") != "active":
            continue
        key = (str(rule.get("entity")), str(rule.get("field")), str(rule.get("scope", "global")))
        rule_id = str(rule.get("rule_id"))
        if key in active_keys and active_keys[key] != rule_id:
            findings.append(
                _finding(
                    "AUTH.ACTIVE_RULE_COLLISION",
                    f"Active rules {active_keys[key]} and {rule_id} share entity/field/scope {key}",
                    snapshot_path,
                )
            )
        active_keys[key] = rule_id
    return findings


def _references(record: dict[str, Any]) -> set[str]:
    refs: set[str] = set()
    for field in ("links", "source_ids", "decision_ids", "supersedes"):
        value = record.get(field, [])
        if isinstance(value, list):
            refs.update(str(item) for item in value if isinstance(item, str))
    return refs


def _validate_graph(manifest: dict[str, Any], records: list[dict[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    nodes = {str(record["id"]): record for record in records if isinstance(record.get("id"), str)}
    roots = manifest.get("root_nodes", [])
    if not nodes:
        return findings
    if not roots:
        return [
            _finding(
                "GRAPH.NO_ROOTS",
                "The project contains records but project.yaml root_nodes is empty",
                "project.yaml",
            )
        ]
    unknown_roots = [root for root in roots if root not in nodes]
    for root in unknown_roots:
        findings.append(
            _finding("GRAPH.ROOT_MISSING", f"Root node does not exist: {root}", "project.yaml")
        )

    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for node_id, record in nodes.items():
        for ref in _references(record):
            if ref in nodes:
                adjacency[node_id].add(ref)
                adjacency[ref].add(node_id)
            else:
                findings.append(
                    _finding(
                        "GRAPH.REFERENCE_MISSING",
                        f"Node {node_id} references missing node {ref}",
                        str(record.get("_path")),
                    )
                )
    queue = deque(root for root in roots if root in nodes)
    reached = set(queue)
    while queue:
        current = queue.popleft()
        for neighbour in adjacency[current]:
            if neighbour not in reached:
                reached.add(neighbour)
                queue.append(neighbour)
    for node_id in sorted(set(nodes) - reached):
        findings.append(
            _finding(
                "GRAPH.DISCONNECTED",
                f"Node {node_id} is not reachable from any declared root",
                str(nodes[node_id].get("_path")),
            )
        )
    return findings


def _validate_secrets(project_root: Path) -> list[Finding]:
    findings: list[Finding] = []
    excluded_parts = {".git", ".venv", "__pycache__"}
    for path in sorted(project_root.rglob("*")):
        if not path.is_file() or any(part in excluded_parts for part in path.parts):
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            continue
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(
                    _finding(
                        "SECURITY.POSSIBLE_SECRET",
                        f"Possible {name} detected; secrets must not be stored in the repository",
                        path.relative_to(project_root),
                    )
                )
    return findings


def validate_project(project_root: Path) -> ValidationReport:
    """Run all deterministic validation layers and return every finding."""
    root = project_root.resolve()
    manifest, findings = _validate_manifest(root)
    if manifest is None:
        return ValidationReport(tuple(findings))

    loaded: dict[str, list[dict[str, Any]]] = {}
    for kind in RECORD_DIRECTORIES:
        loaded[kind], new_findings = _load_records(root, kind)
        findings.extend(new_findings)
    all_records = [record for records in loaded.values() for record in records]
    findings.extend(_validate_unique_ids(all_records))

    project_id = manifest.get("project_id")
    if isinstance(project_id, str):
        findings.extend(_validate_project_ids(project_id, all_records))
    findings.extend(_validate_sources(root, loaded["source"]))
    findings.extend(_validate_traceability(loaded["source"], loaded["decision"], loaded["output"]))
    findings.extend(_validate_authority(root, loaded["decision"]))
    findings.extend(_validate_graph(manifest, all_records))
    findings.extend(_validate_secrets(root))

    findings.sort(
        key=lambda item: (item.severity != "error", item.code, item.path or "", item.message)
    )
    return ValidationReport(tuple(findings))
