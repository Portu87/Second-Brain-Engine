# Architecture

Second Brain Engine separates storage roles so that evidence, authorization, current state and
presentation cannot silently overwrite one another.

## Engine versus project

The engine contains reusable code, schemas, policies, tests and workflows. A project contains only
its own manifest and records. Adding a project must not require editing engine validators.

## Project layers

### Sources

`sources/raw/` stores copied evidence. `sources/records/` stores metadata, classification, origin,
path, size and digest. Raw evidence is append-only. Corrections are new sources; withdrawal changes
metadata rather than rewriting bytes.

### Decisions

`decisions/` stores immutable decision events. Only `approved` events affect canonical state.
Proposed or rejected records remain visible but have no authority.

### Canon

`canon/snapshot.json` is a build artifact. The compiler orders approved decisions deterministically,
applies supported operations and records provenance on each rule. Validation recompiles in memory
and compares semantic content, making manual edits and stale state detectable.

### Knowledge

`knowledge/` is reserved for candidate observations, extracted entities and interpretations. It is
not authoritative in version 0.1 and cannot directly alter canon.

### Outputs

`outputs/` records derived artifacts and the exact canon digest, decisions and sources used. Outputs
are consumers of authority, never producers.

### Pending and history

`pending/` stores structured work records. `history/` is reserved for snapshots, migrations and
rollback evidence. Neither directory is considered current truth.

## Determinism

Compilation order is `effective_from`, then `decided_at`, then decision ID. Rules are serialized by
rule ID. The semantic snapshot receives a SHA-256 digest before the non-semantic generation time is
added. Recompilation with unchanged decisions therefore yields the same canonical content digest.

## Failure posture

The engine fails closed for malformed schemas, missing sources, checksum changes, unsupported
operations, unresolved references, stale canon and disconnected graphs. Heuristics such as secret
scanning may produce false positives, but are intentionally blocking until reviewed.
