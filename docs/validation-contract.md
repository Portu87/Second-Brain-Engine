# Validation contract

Validation is deterministic and returns every discovered finding in stable order.

## Severity

`error` blocks the project. `warning` is reserved for non-authoritative quality signals. Version 0.1
uses blocking errors for all implemented checks.

## Code families

- `STRUCTURE.*`: syntax, schema, IDs and project boundaries;
- `SOURCE.*`: raw source integrity and safe storage;
- `TRACE.*`: provenance and referential integrity;
- `AUTH.*`: compilation, canonical state and authority collisions;
- `GRAPH.*`: roots, references and reachability;
- `SECURITY.*`: likely credentials or private keys.

Consumers must use exit status rather than parsing human prose. JSON output includes `ok`, counts and
structured findings. Finding codes are the stable automation interface; wording may improve over time.
