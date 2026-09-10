# `States:`

Use `States:` to define a reusable command-backed proposition. The `States:`
line itself takes no argument; the proposition body belongs in `that:`.

```text
[P \.implies./ Q]
States:
when: P, Q is \\statement
that:
. if: P
  then: Q
Documented:
. called: "$P?$ implies $Q?$"
. written: "P? \Rightarrow Q?"
```

Allowed order is `States`, `using?`, `when?`, required `that:`, then
`Requires?`, `Enables?`, `Documented?`, `Justification?`, `Aliases?`,
`Writing?`, `References?`, `Metadata?`.

Use [clause groups](../../mathlingua-clause-groups/SKILL.md) inside `that:` and
[statement syntax](../../mathlingua-formulation-language/references/statements-and-specifications.md)
for inline assertions.

## Anti-patterns

- Do not write a proposition after `States:` itself.
- Do not use `States:` for a one-off mathematical result; use `Theorem:` or the
  appropriate theorem-like group.
- Do not bind a new symbol only in the conclusion; introduce it in `when:` or a
  nested binding clause.
