from __future__ import annotations

from pathlib import Path

import pytest

from second_brain_engine.errors import ProjectError
from second_brain_engine.io import load_json, load_yaml, sha256_file
from second_brain_engine.schema import schema_errors


def test_loaders_reject_non_mapping_roots_and_invalid_json(tmp_path: Path) -> None:
    yaml_path = tmp_path / "list.yaml"
    yaml_path.write_text("- one\n- two\n", encoding="utf-8")
    with pytest.raises(ProjectError, match="YAML root"):
        load_yaml(yaml_path)

    json_path = tmp_path / "bad.json"
    json_path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ProjectError, match="JSON root"):
        load_json(json_path)


def test_sha256_rejects_directories(tmp_path: Path) -> None:
    with pytest.raises(ProjectError, match="regular file"):
        sha256_file(tmp_path)


def test_schema_errors_include_paths() -> None:
    messages = schema_errors("project", {"schema_version": "0"})
    assert messages
    assert any("required property" in message or "was expected" in message for message in messages)
