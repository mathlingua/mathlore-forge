# `expresses:`

Use `expresses:` in `Defines:` or `Realizes:` for the body that supplies a
value, especially a callable or piecewise component whose type was stated in
`Defines:` or `specifies:`.

```text
[\identity:on{A}]
Defines: f(x__) is \function:on{A}:to{A}
when: A is \set
expresses: f(x__) := x__
```

The section accepts one clause. Function-form input specifications from the
declared type are assumptions while the body is checked. A
[piecewise clause](../../mathlingua-clause-groups/references/piecewise.md) may
supply a branch-defined value.

## Anti-patterns

- Do not add several unrelated bodies; `expresses:` is singular.
- Do not omit the value for a typed concrete component.
- Do not define an output using symbols unavailable from the heading, `using:`,
  `when:`, or function inputs.
