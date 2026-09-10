# `allOf:`

Use `allOf:` when every nested clause must hold. When the group is assumed, its
children's facts are gathered for later checks.

```text
. allOf:
  . x "in" A
  . P(x)
```

Read [logical collections](logical-collections.md) for shared syntax.

## Anti-patterns

- Do not use `allOf:` when the clauses are alternatives.
- Do not assume a child may use facts introduced by a later sibling.
