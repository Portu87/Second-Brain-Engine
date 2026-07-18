"""Safe filesystem and serialization helpers."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .errors import ProjectError

YAML_SUFFIXES = {".yaml", ".yml"}


def load_yaml(path: Path) -> dict[str, Any]:
    """Load one YAML mapping with safe parsing and useful errors."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ProjectError(f"Cannot read YAML file {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProjectError(f"YAML root must be a mapping: {path}")
    return raw


def dump_yaml(data: dict[str, Any]) -> str:
    """Serialize YAML deterministically enough for version control."""
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100)


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectError(f"Cannot read JSON file {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProjectError(f"JSON root must be an object: {path}")
    return raw


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically replace a UTF-8 text file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Atomically write canonical, human-readable JSON."""
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest for a regular file."""
    if not path.is_file():
        raise ProjectError(f"Expected a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_yaml_files(directory: Path) -> list[Path]:
    """Return YAML files recursively in stable order."""
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in YAML_SUFFIXES
    )
