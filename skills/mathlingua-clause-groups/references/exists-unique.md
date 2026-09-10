# `existsUnique:`

Use `existsUnique:` when exactly one locally bound value satisfying the optional
conditions is intended.

```text
. existsUnique: e "in" M
  suchThat:
  . forAll: x "in" M
    then: e * x = x
```

Read [existence syntax](existence.md) for binding and scope rules.

## Anti-patterns

- Do not use unique existence without a mathematically justified uniqueness
  claim.
- Do not assume the checker proves uniqueness.
