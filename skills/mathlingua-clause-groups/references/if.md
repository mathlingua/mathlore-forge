# `if:`

Use `if:` for an implication: assume one or more conditions and check one or
more required consequences.

```text
. if:
  . P
  . x "in" A
  then:
  . Q
```

Facts from `if:` are available while checking `then:`. For branch selection in
a value definition, use [`piecewise:`](piecewise.md).

## Anti-patterns

- Do not omit `then:`.
- Do not expect facts introduced in `then:` to escape the conditional.
- Do not use `if:` where an equivalence is intended; use `have`/`iff` or
  `equivalently` as appropriate.
