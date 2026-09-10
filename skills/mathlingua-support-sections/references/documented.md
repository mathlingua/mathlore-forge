# `Documented:`

Use `Documented:` for reader-facing names, notation, and explanation.

```text
Documented:
. called: "function from $A?$ to $B?$"
. written: "A? \\rightarrow B?"
. description: "A mapping assigning each element of $A?$ an element of $B?$."
```

Definition groups normally require at least `called:` or `written:`. `Refines:`
requires `adjective:` and rejects `called:`. Other available fields include
`writing:`/`as:`, `overview:`, `related:`, `discoverer:`, and `notes:`; use them
only where the parent group accepts them and where a nearby example establishes
the convention.

For placeholder substitution and notation, read
[rendering templates](../../mathlore-prose-content/references/rendering-templates.md).

## Anti-patterns

- Do not use `called:` for a refinement.
- Do not copy a `written:` template without matching its placeholders to the
  current heading.
- Do not repeat the formula as a low-value `description:`.
