# Contributing

1. Create a focused branch.
2. Add or update tests for every behavior change.
3. Run `make check` locally.
4. Keep domain-specific facts out of engine code and fixtures.
5. Preserve backward compatibility of finding codes or document a migration.
6. Do not weaken a blocking invariant merely to make a fixture pass.

Changes to schemas, authority semantics, compilation order, privacy rules or CI gates require an
explicit design explanation in the pull request.
