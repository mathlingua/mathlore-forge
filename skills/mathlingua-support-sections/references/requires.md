# `Requires:`

Use `Requires:` to record notation or definitions that are part of what a
construct needs.

```text
Requires:
. capability: x_ * y_ :=> \multiply{x_, y_}
. definition: \zero is \distinguished.element
```

`capability:` accepts expression aliases or specification implication/equivalence
forms. `definition:` requires the referenced command to be a top-level
`Defines:` whose definition establishes the requested fact. Requirements are
checked at command use sites.

See [aliases and capability arrows](../../mathlingua-formulation-language/references/aliases-and-capabilities.md).

## Anti-patterns

- Do not put reader-facing prerequisites here; this section affects semantics.
- Do not require a definition that is merely `Declares:`.
- Do not remove a requirement just to permit an otherwise invalid command use.
