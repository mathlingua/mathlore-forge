# `Theorem:`

Use `Theorem:` for a standalone result the collection presents as established.
Its syntax is the shared [theorem-like shape](theorem-like-groups.md).

```text
Theorem:
given: X is \set
where: x "in" X
then: x is? \\anything
Documented:
. called: "example theorem"
```

Review the mathematical claim independently of the checker and add an
appropriate source or justification when needed.

## Anti-patterns

- Do not promote an unverified or open claim to theorem status.
- Do not weaken types or hypotheses merely to make checking pass.
- Do not confuse a clean semantic check with a proof.
