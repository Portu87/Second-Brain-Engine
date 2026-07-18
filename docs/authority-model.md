# Authority model

The engine uses compiled-state authority.

1. A source is evidence, not truth by itself.
2. A decision authorizes a precise state transition and cites evidence.
3. The compiler applies approved decisions in deterministic order.
4. The canonical snapshot represents current machine-readable state.
5. Validators prove that the snapshot is exactly the result of those decisions.
6. Outputs cite the snapshot and cannot modify it.

This removes the ambiguous question “does canon or the latest decision win?” The decision authorizes;
the compiled canon represents the applied result. History explains how the result was reached.

## Invariants

- Project facts never appear as constants in engine code.
- Approved decisions cite at least one registered source.
- Canon is generated, never manually maintained.
- A rule carries its creating decision and sources.
- One active rule may occupy an entity/field/scope tuple.
- Deactivation requires an existing rule.
- Unknown operations stop compilation.
- A stale or edited snapshot blocks validation.
- Derived outputs cannot become authority through directory placement or wording.
