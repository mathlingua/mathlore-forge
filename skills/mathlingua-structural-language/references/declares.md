# `Declares:`

Use `Declares:` for a reusable mathematical type, interface, relation shape, or
statement shape. It describes facts every instance carries; it does not supply
a concrete value.

```text
[\magma]
Declares: M ::= (X, *) is \set via X
specifies:
. * is \binary.operation:on{X}
Documented:
. called: "magma"
. description: "A set equipped with a binary operation."
```

Allowed section order is `Declares`, `using?`, `when?`, `extends?`,
`specifies?`, `satisfies?`, `Requires?`, `Enables?`, `Documented?`,
`Justification?`, `Aliases?`, `Writing?`, `References?`, `Metadata?`.

- `::=` declares a structural expansion; `via` identifies the form through
  which the new type extends another type.
- Put parameter facts in `when:`. The symbol described by the target is the
  usual exception.
- Use `specifies:` for facts carried by every instance, including component
  types. Use `satisfies:` for proposition clauses.
- `Documented:` needs at least one `called:` or `written:` entry.

See [forms and declarations](../../mathlingua-formulation-language/references/forms-and-declarations.md),
[`extends:`](../../mathlingua-support-sections/references/extends.md), and
[`specifies:`](../../mathlingua-support-sections/references/specifies.md).

## Anti-patterns

- Do not use `Declares:` to assign a concrete value; use `Defines:`.
- Do not use `:=` where a structural expansion needs `::=`.
- Do not repeat one component's base fact in incompatible ways.
- Do not add a new command path before searching for an existing concept.
