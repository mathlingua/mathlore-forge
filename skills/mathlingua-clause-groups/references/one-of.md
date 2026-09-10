# `oneOf:`

Use `oneOf:` when the assertion has one-of intent rather than merely at-least-one
intent.

```text
. oneOf:
  . P
  . Q
```

Read [logical collections](logical-collections.md) for shared syntax.

## Anti-patterns

- Do not assume the checker proves pairwise exclusivity.
- Do not use `oneOf:` when overlapping alternatives are acceptable.
