"""JSON Schema loading and validation."""

from __future__ import annotations

import json
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_FILES = {
    "project": "project.schema.json",
    "source": "source.schema.json",
    "decision": "decision.schema.json",
    "snapshot": "snapshot.schema.json",
    "output": "output.schema.json",
    "pending": "pending.schema.json",
}


def _source_checkout_schema_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "schemas"


@cache
def load_schema(name: str) -> dict[str, Any]:
    """Load a bundled schema, with a source-checkout fallback."""
    filename = SCHEMA_FILES[name]
    checkout = _source_checkout_schema_dir() / filename
    if checkout.is_file():
        return cast(dict[str, Any], json.loads(checkout.read_text(encoding="utf-8")))
    resource = files("second_brain_engine").joinpath("schemas", filename)
    return cast(dict[str, Any], json.loads(resource.read_text(encoding="utf-8")))


def schema_errors(name: str, instance: dict[str, Any]) -> list[str]:
    """Return stable, human-readable schema failures."""
    validator = Draft202012Validator(load_schema(name), format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path))
    messages: list[str] = []
    for error in errors:
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        messages.append(f"{location}: {error.message}")
    return messages
