# `allOf:`, `anyOf:`, And `oneOf:`

For construct-specific usage, read [`allOf:`](all-of.md),
[`anyOf:`](any-of.md), or [`oneOf:`](one-of.md).

Use these groups to combine one or more clauses:

```text
. allOf:
  . P
  . Q

. anyOf:
  . P
  . Q

. oneOf:
  . P
  . Q
```

`allOf:` means every child, `anyOf:` means at least one, and `oneOf:` expresses
one-of intent. The checker validates every child. When `allOf:` is assumed, it
gathers facts from all children; do not expect the same fact accumulation from
alternatives.

Inline builtin forms such as `\\allOf{P, Q}` exist in statement positions and
obey the same scope rules.

## Anti-patterns

- Do not use an alternatives group when later clauses require facts available
  only from one branch.
- Do not provide an empty collection.
- Do not assume `oneOf:` proves mutual exclusivity automatically.
