# Second Brain Engine

Second Brain Engine is a project-agnostic framework for building trustworthy knowledge systems.
It separates immutable evidence, human-approved decisions, compiled canonical state, derived
outputs, pending work, and history so that no document, script, or AI agent silently becomes a
second source of truth.

> Sources preserve evidence. Decisions authorize change. The compiler produces current state.
> Validators verify that state. Outputs never write back into authority.

## Status

Version `0.1.0` is an alpha foundation. It already provides executable controls for the failure
modes that commonly corrupt growing second brains: duplicated authority, stale canon, modified
sources, missing provenance, broken references, disconnected knowledge graphs, malformed YAML,
hard-coded project facts, and CI gaps.

## Core model

```text
immutable sources
      │
      ▼
approved decision events
      │
      ▼
deterministic compiler ──► canon/snapshot.json
      │                         │
      └──────── validation ◄────┘
                                │
                                ▼
                         derived outputs
```

The canonical snapshot is generated. Editing it manually is a validation failure. Domain facts
belong in project records, never in engine source code.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Start a project

```bash
sbe init ./projects/example --id example-project --name "Example Project" --language en
sbe validate ./projects/example
```

The initialized project is intentionally empty:

```text
project.yaml
sources/
  raw/
  records/
decisions/
canon/
knowledge/
pending/
outputs/
history/
config/
```

## Ingest immutable evidence

```bash
sbe ingest ./projects/example ./notes/interview.txt \
  --id SRC-INTERVIEW-001 \
  --title "Discovery interview" \
  --origin "Internal interview, 2026-07-18" \
  --classification internal
```

The engine copies the file into append-only storage and records its SHA-256 and byte size. A later
change to the raw file fails validation instead of being silently accepted.

## Authorize a change

Create a decision event under `decisions/` using `schemas/decision.schema.json`. Approved decisions
contain explicit operations such as `upsert_rule` and `deactivate_rule`. Every approved decision
must cite at least one registered source.

```yaml
schema_version: "1.0"
id: DEC-EXAMPLE-001
project_id: example-project
title: Define the support response target
status: approved
decided_at: "2026-07-18T12:00:00Z"
effective_from: "2026-07-18T12:00:00Z"
approved_by: project-owner
source_ids:
  - SRC-INTERVIEW-001
rationale: The source establishes the accepted operating target.
operations:
  - op: upsert_rule
    rule:
      rule_id: operations.support.response-target
      entity: support
      field: response_target_hours
      value: 24
      scope: global
supersedes: []
links: []
```

Then compile and validate:

```bash
sbe compile ./projects/example
sbe validate ./projects/example
```

## Validation layers

`validate` reports all deterministic failures in one run:

- structural schemas, safe YAML/JSON parsing, IDs, project boundaries and duplicates;
- immutable source checksum, size, path safety and path reuse;
- decision/output provenance and missing references;
- deterministic canon equality, stale snapshots, unsupported operations and active-rule collisions;
- graph roots, missing references and components disconnected from declared roots;
- basic secret scanning for private keys, common tokens and credential-like assignments.

Use machine-readable output in automation:

```bash
sbe validate ./projects/example --json
```

Exit codes are stable: `0` valid, `1` validation failures, `2` command or project error.

## Development

```bash
make check
```

This runs formatting checks, linting, strict type checking, tests and coverage. GitHub Actions runs
the same gates on every pull request and push to `main`, across supported Python versions.

## Security boundary

The engine helps enforce provenance and repository hygiene; it is not a secrets vault, clinical
record system, access-control platform, or legal compliance product. Do not commit prohibited or
unnecessary sensitive data. See [SECURITY.md](SECURITY.md) and [docs/threat-model.md](docs/threat-model.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Authority model](docs/authority-model.md)
- [Threat model](docs/threat-model.md)
- [Validation contract](docs/validation-contract.md)
- [Roadmap](docs/roadmap.md)

## License

MIT.
