# `Defines:`

Use `Defines:` for a command that denotes a concrete value or operation, or for
an intentionally open definition marked `abstractly:`.

```text
[\intersection:of{A}:and{B}]
Defines: I is \set
when: A, B is \set
expresses: I := \set@{x_ : x_ "in" A | x_ "in" B}
Documented:
. called: "intersection of $A?$ and $B?$"
```

Allowed order is `Defines`, `abstractly?`, `using?`, `when?`, `specifies?`,
`expresses?`, `Requires?`, `Enables?`, `Documented?`, `Justification?`,
`Aliases?`, `Writing?`, `References?`, `Metadata?`.

- Every concrete definition needs an explicit type, through `is` or a top-level
  build expression.
- For a destructured target, every component needs a value through `:=` or
  `expresses:`.
- `abstractly:` intentionally leaves typed components open for a later
  `Realizes:` group:

```text
[\naturals]
Defines: Nb ::= (N, 0, succ(n_))
abstractly:
specifies:
. N is \set
. 0 "in" N
. succ is \function:on{N}:to{N}
```

See [`expresses:`](../../mathlingua-support-sections/references/expresses.md)
and [direct components](../../mathlingua-formulation-language/references/operators-and-members.md).

## Anti-patterns

- Do not define a value without a type.
- Do not leave a concrete destructured component with only a specification and
  no value.
- Do not add `abstractly:` just to silence an incomplete definition; use it only
  when a realization is part of the design.
- Do not write rendered one-dot direct access in source; command components use
  `..`, such as `\naturals..N`.
