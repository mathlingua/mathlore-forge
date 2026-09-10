# `Equivalent:`

Use `Equivalent:` to register compatible commands as interchangeable under a
shared command heading.

```text
[\common.presentation{A}]
Equivalent:
when: A is \set
to:
. \first.presentation{A}
. \second.presentation{A}
Documented:
. called: "equivalent presentations of $A?$"
```

Each `to:` member must be defined, use the heading parameters directly, and be
the same group kind (`Declares`, `Defines`, `States`, or `Refines`) as every
other member. Members must agree on target shape and kind-specific type/base
facts, and expose the same capability names and arities. This group's `when:`
must guarantee each member's requirements.

Order is `Equivalent`, `using?`, `when?`, required `to`, `Documented?`,
`Justification?`, `References?`.

## Anti-patterns

- Do not mix definition kinds or merely similar-looking commands.
- Do not pass compound expressions or `using:` symbols as member parameters.
- Do not use `Equivalent:` for a theorem asserting equality; it changes command
  substitutability in the checker.
