# `anyOf:`

Use `anyOf:` when at least one nested alternative should hold.

```text
. anyOf:
  . x < 0
  . x = 0
  . x > 0
```

Read [logical collections](logical-collections.md) for shared syntax.

## Anti-patterns

- Do not expect facts from one alternative to become unconditional afterward.
- Do not use `anyOf:` when exactly one alternative is mathematically required.
