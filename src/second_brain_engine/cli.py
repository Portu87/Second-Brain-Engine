"""Command-line interface for Second Brain Engine."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .compiler import compile_project
from .errors import SecondBrainError
from .project import ingest_source, init_project
from .validator import validate_project


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sbe", description="Second Brain Engine")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_cmd = subparsers.add_parser("init", help="Initialize an empty project")
    init_cmd.add_argument("path", type=Path)
    init_cmd.add_argument("--id", required=True, dest="project_id")
    init_cmd.add_argument("--name", required=True)
    init_cmd.add_argument("--language", default="en")

    ingest_cmd = subparsers.add_parser("ingest", help="Ingest one immutable source")
    ingest_cmd.add_argument("project", type=Path)
    ingest_cmd.add_argument("file", type=Path)
    ingest_cmd.add_argument("--id", required=True, dest="source_id")
    ingest_cmd.add_argument("--title", required=True)
    ingest_cmd.add_argument("--origin", required=True)
    ingest_cmd.add_argument("--classification", default="internal")

    compile_cmd = subparsers.add_parser("compile", help="Compile approved decisions")
    compile_cmd.add_argument("project", type=Path)

    validate_cmd = subparsers.add_parser("validate", help="Run all deterministic checks")
    validate_cmd.add_argument("project", type=Path)
    validate_cmd.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            path = init_project(args.path, args.project_id, args.name, args.language)
            print(f"Initialized {path}")
            return 0
        if args.command == "ingest":
            path = ingest_source(
                args.project,
                args.file,
                args.source_id,
                title=args.title,
                origin=args.origin,
                classification=args.classification,
            )
            print(f"Registered {path}")
            return 0
        if args.command == "compile":
            path = compile_project(args.project)
            print(f"Compiled {path}")
            return 0
        if args.command == "validate":
            report = validate_project(args.project)
            if args.as_json:
                print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
            else:
                status = "PASS" if report.ok else "FAIL"
                print(f"{status}: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
                for finding in report.findings:
                    location = f" [{finding.path}]" if finding.path else ""
                    print(
                        f"- {finding.severity.upper()} {finding.code}{location}: {finding.message}"
                    )
            return 0 if report.ok else 1
    except SecondBrainError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    parser.error("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
