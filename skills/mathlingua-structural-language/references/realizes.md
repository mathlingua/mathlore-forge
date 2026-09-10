# `Realizes:`

Use `Realizes:` to supply every open component of a `Defines:` command marked
`abstractly:`.

```text
[\von.neumann.naturals]
Realizes: Nb := \naturals
specifies:
. N := \von.neumann.omega
. 0 := \empty.set
. succ(n_) := n_ \union \set@{n_}
Documented:
. called: "von Neumann naturals"
```

The right side of `:=` must name an abstract `Defines:` command, not a
`Declares:` type. Supply all symbols left open by the abstract definition.
Component types are inherited, so use `specifies:` for values and
`expresses:` when a callable body supplies the value indirectly.

Allowed order is `Realizes`, `using?`, `when?`, `specifies?`, `expresses?`,
then the same support sections as `Defines:`.

## Anti-patterns

- Do not write `Realizes: X is \abstract.command`; realizations use `:=`.
- Do not omit an abstract component or invent a component absent from the base.
- Do not realize an ordinary concrete `Defines:` command.
- Do not change inherited component types merely to make assignments pass.
