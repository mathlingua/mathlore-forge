# `extends:`

Use `extends:` only in `Declares:` to state that the newly declared type is a
subtype of one or more existing types. Each item is a declaration statement and
may include `via` to identify the corresponding structural form.

```text
[\group]
Declares: G ::= (X, *, e)
extends: G is \monoid via (X, *, e)
```

The declared target gains the base type's facts and capabilities. Ensure the
target and `via` form structurally align with the base declaration.

You can equivalently, in a `Declares:` use the shorter notation
```
[\group]
Declares: G ::= (X, *, e) is \monoid via (X, *, e)
```

Use the `extends:` group to specify that the type is a sub-type of many different
types through different selection of items from a tuple as in
```
[\foo]
Declares: F ::= (X, *, +, 0, 1)
extends:
. F is \bar via (X, +, 0)
. F is \baz via (X, *, 1)
```

## Anti-patterns

- Do not use `extends:` under `Defines:` or `Refines:`.
- Do not treat `extends:` as narrative inheritance; it changes semantic facts.
- Do not omit the needed structural mapping when the child and base forms differ.
