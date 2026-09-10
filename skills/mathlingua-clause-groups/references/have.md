# `have:` Forms

Two structural groups begin with `have:`.

Use `have:` followed by required `iff:` for a biconditional:

```text
. have: P
  iff: Q
```

Use proof-style `have:` with optional `asserting:`, `because:`, and `by:` to
record an assertion and its support:

```text
. have: x = z
  asserting: x = y
  because: y = z
```

The proof-style form is also used by labeled entries under `Justification:`;
see [justification](../../mathlingua-support-sections/references/justification.md).

## Anti-patterns

- Do not swap section order; `asserting:`, `because:`, then `by:` is fixed.
- Do not assume `have:` is a free-form proof paragraph; its children are checked
  clauses or expressions.
- Do not use an unlabeled proof-style entry under `Justification:`.
