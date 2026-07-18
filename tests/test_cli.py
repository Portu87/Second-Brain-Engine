from __future__ import annotations

import json
from pathlib import Path

from second_brain_engine.cli import main


def test_cli_init_validate_and_error_exit(tmp_path: Path, capsys: object) -> None:
    root = tmp_path / "project"
    assert main(["init", str(root), "--id", "cli-project", "--name", "CLI Project"]) == 0
    assert main(["validate", str(root), "--json"]) == 0

    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out.split("\n", 1)[1])
    assert payload["ok"] is True

    assert main(["compile", str(tmp_path / "missing")]) == 2


def test_cli_ingest_compile_and_human_validation(tmp_path: Path, capsys: object) -> None:
    root = tmp_path / "project"
    source = tmp_path / "source.txt"
    source.write_text("evidence", encoding="utf-8")
    assert main(["init", str(root), "--id", "cli-second", "--name", "CLI Second"]) == 0
    assert (
        main(
            [
                "ingest",
                str(root),
                str(source),
                "--id",
                "SRC-CLI-001",
                "--title",
                "CLI source",
                "--origin",
                "Fixture",
            ]
        )
        == 0
    )
    assert main(["compile", str(root)]) == 0
    assert main(["validate", str(root)]) == 1
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "GRAPH.NO_ROOTS" in captured.out
