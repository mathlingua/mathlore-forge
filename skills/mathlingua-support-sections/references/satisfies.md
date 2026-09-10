# `satisfies:`

Use `satisfies:` in `Declares:` or `Refines:` for proposition clauses every
instance of the type or refinement must satisfy.

```text
satisfies:
. forAll: x "in" X
  then: x * e = x
```

The section accepts one or more inline clauses or nested
[clause groups](../../mathlingua-clause-groups/SKILL.md). Component and
parameter facts established earlier in the group are available.

## Anti-patterns

- Do not use `satisfies:` to assign component values.
- Do not introduce a fresh unbound symbol directly in a conclusion.
- Do not duplicate a type fact that belongs in `specifies:`.
