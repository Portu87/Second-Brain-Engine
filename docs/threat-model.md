# Threat model

## Protected assets

- integrity and provenance of source evidence;
- correctness of canonical state;
- separation between candidate knowledge and approved authority;
- reproducibility of compilation;
- confidentiality classifications and absence of committed credentials;
- auditability of changes through Git and decision events.

## Primary threats

- accidental editing of raw evidence;
- malformed or permissively parsed metadata;
- duplicate IDs and cross-project references;
- a script hard-coding business facts;
- canon edited manually or left stale after decisions change;
- an output or historical file treated as current truth;
- missing provenance;
- disconnected graph components hidden from navigation;
- secrets committed to a public or shared repository;
- validators present locally but absent from CI.

## Controls in version 0.1

- SHA-256 and byte-size verification for every source;
- safe YAML loading and JSON Schema Draft 2020-12;
- strict project and record identifiers;
- deterministic event compilation and snapshot comparison;
- traceability checks and project-boundary checks;
- graph root reachability;
- secret heuristics;
- lint, strict typing, unit tests and coverage in CI;
- Dependabot and CodeQL workflows.

## Out of scope

Version 0.1 does not provide encryption at rest, user authentication, row-level authorization,
remote object locking, data-loss prevention, legally sufficient deletion, or regulatory compliance.
Those controls belong in the deployment environment and future storage adapters.
