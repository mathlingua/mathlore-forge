# `exists:`

Use `exists:` when at least one locally bound value with optional conditions is
asserted to exist.

```text
. exists: y "in" Y
  suchThat: f(x) = y
```

Read [existence syntax](existence.md) for binding and scope rules.

## Anti-patterns

- Do not use the bound value outside this clause.
- Do not choose `exists:` when uniqueness is part of the intended claim.
