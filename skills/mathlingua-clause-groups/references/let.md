# `let:`

Use `let:` for one or more local bindings used in an optional guard and a
required body.

```text
. let: y := f(x)
  where: y != x
  then: y "in" Y
```

Bindings may use declaration/specification forms. `where:` assumptions and the
new values are available in `then:` only. Use this construct for local
assumptions as well as local values; nested `given:` clause groups are not part
of the structural language.

## Anti-patterns

- Do not omit `then:`.
- Do not use a name already defined in an inherited context.
- Do not reference the local value after the `let:` group ends.
- Do not use `let:` when the value is a reusable top-level definition.
