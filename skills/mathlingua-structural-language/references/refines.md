# `Refines:`

Use `Refines:` for an adjective or property that specializes an existing
`Declares:` type or specification operator.

```text
[A \:(proper)::subset:/ B]
Refines: A
when: B is \set
specifies: A \:subset:/ B
satisfies: A != B
Documented:
. adjective: "proper"
. written: "A? \\subsetneq B?"
```

The target must agree with the base declaration's shape, but may omit trailing
detail it does not need. `Documented:` requires `adjective:` and rejects
`called:`. Refined types use `\(continuous)::function:on{A}:to{B}`; multiple
adjectives are comma-separated inside the parentheses.

Allowed order is `Refines`, `implicitly?` or `explicitly?`, `using?`, `when?`,
`specifies?`, `satisfies?`, then the standard support sections.

- Use `implicitly:` only to restate an inherited refinement on a subtype. Its
  body may contain only the inherited `specifies:` fact plus scaffolding.
- Use `explicitly:` when the subtype refinement adds a property such as
  `satisfies:` beyond the inherited fact.
- Use neither marker when the base is not itself a subtype.
- `[[subject]]` in `specifies:` refers to the enclosing base type; copy a nearby
  checked use before relying on it.

See [refined commands](../../mathlingua-formulation-language/references/refined-commands.md).

## Anti-patterns

- Do not use `called:` for a refinement.
- Do not change the structural shape of the base target.
- Do not mark a stronger refinement `implicitly:` or a trivial inherited one
  `explicitly:`.
- Do not use `Refines:` to create an unrelated subtype; the adjective must
  refine the command named by the heading.
