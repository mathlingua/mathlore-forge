# `equivalently:`

Use `equivalently:` for a chain of two or more formulations intended to be
pairwise biconditional.

```text
. equivalently:
  . P
  . Q
  . R
```

It is concise sugar for an equivalence chain. Use the clauses in a logical
order that a reader can follow.

## Anti-patterns

- Do not use it for mere equality of values or interchangeable command
  definitions.
- Do not rely on prose order to bind symbols; every symbol still needs a valid
  declaration in scope.
- Do not provide a single-item chain.
