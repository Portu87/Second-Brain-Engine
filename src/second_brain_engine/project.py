"""Project initialization and immutable source ingestion."""

from __future__ import annotations

import mimetypes
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from .errors import ProjectError
from .io import atomic_write_text, dump_yaml, sha256_file

PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
SOURCE_ID_RE = re.compile(r"^SRC-[A-Z0-9][A-Z0-9-]{2,63}$")


PROJECT_DIRS = (
    "sources/raw",
    "sources/records",
    "decisions",
    "canon",
    "knowledge",
    "pending",
    "outputs",
    "history",
    "config",
)


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def init_project(root: Path, project_id: str, name: str, language: str = "en") -> Path:
    """Create an empty project with no domain-specific knowledge."""
    if not PROJECT_ID_RE.fullmatch(project_id):
        raise ProjectError("project_id must match ^[a-z][a-z0-9-]{2,63}$")
    if root.exists() and any(root.iterdir()):
        raise ProjectError(f"Refusing to initialize a non-empty directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for directory in PROJECT_DIRS:
        (root / directory).mkdir(parents=True, exist_ok=True)
        (root / directory / ".gitkeep").touch()

    manifest = {
        "schema_version": "1.0",
        "project_id": project_id,
        "name": name,
        "language": language,
        "status": "active",
        "authority_model": "compiled-state",
        "confidentiality_default": "internal",
        "root_nodes": [],
        "created_at": utc_now(),
    }
    atomic_write_text(root / "project.yaml", dump_yaml(manifest))
    atomic_write_text(
        root / "README.md",
        f"# {name}\n\nProject ID: `{project_id}`.\n\nRun `sbe validate .` before commits.\n",
    )
    return root


def ingest_source(
    project_root: Path,
    source_path: Path,
    source_id: str,
    *,
    title: str,
    origin: str,
    classification: str = "internal",
) -> Path:
    """Copy a source into append-only storage and register its digest."""
    if not SOURCE_ID_RE.fullmatch(source_id):
        raise ProjectError("source_id must match ^SRC-[A-Z0-9][A-Z0-9-]{2,63}$")
    if not source_path.is_file():
        raise ProjectError(f"Source is not a regular file: {source_path}")
    if not (project_root / "project.yaml").is_file():
        raise ProjectError(f"Not an initialized project: {project_root}")

    record_path = project_root / "sources" / "records" / f"{source_id}.yaml"
    if record_path.exists():
        raise ProjectError(f"Source ID already exists: {source_id}")

    safe_name = source_path.name.replace("/", "_").replace("\\", "_")
    raw_relative = Path("sources") / "raw" / source_id / safe_name
    raw_target = project_root / raw_relative
    if raw_target.exists():
        raise ProjectError(f"Raw target already exists: {raw_target}")
    raw_target.parent.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source_path, raw_target)

    digest = sha256_file(raw_target)
    project_id = _project_id(project_root)
    record = {
        "schema_version": "1.0",
        "id": source_id,
        "project_id": project_id,
        "title": title,
        "origin": origin,
        "ingested_at": utc_now(),
        "classification": classification,
        "media_type": mimetypes.guess_type(raw_target.name)[0] or "application/octet-stream",
        "path": raw_relative.as_posix(),
        "sha256": digest,
        "size_bytes": raw_target.stat().st_size,
        "status": "active",
        "links": [],
    }
    atomic_write_text(record_path, dump_yaml(record))
    return record_path


def _project_id(project_root: Path) -> str:
    from .io import load_yaml

    value = load_yaml(project_root / "project.yaml").get("project_id")
    if not isinstance(value, str):
        raise ProjectError("project.yaml has no valid project_id")
    return value
