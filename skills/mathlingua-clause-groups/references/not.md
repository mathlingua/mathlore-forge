# `not:`

Use `not:` to negate exactly one nested clause in the current context.

```text
. not: x "in" A
```

For a compound negation, nest a logical collection:

```text
. not:
  . allOf:
    . P
    . Q
```

## Anti-patterns

- Do not place several sibling arguments directly under `not:`; it accepts one
  clause.
- Do not assume negation creates or binds symbols.
