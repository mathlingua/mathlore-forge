# `Aliases:`

Use `Aliases:` for aliases owned by one top-level item.

```text
Aliases:
. alias: f(x_) :=> x_ + x_
. capability: x_ "in" R :-> x_ is \real
```

`alias:` creates an expression alias with `:=>`. `capability:` uses `:->` for
one-way implication or `:<->:` for equivalence. See
[aliases and capability arrows](../../mathlingua-formulation-language/references/aliases-and-capabilities.md)
for exact formulation syntax.

## Anti-patterns

- Do not use `Aliases:` only to change rendering; use `Writing:` or
  `Documented: written:`.
- Do not assume `:->` permits reverse inference.
- Do not add an alias whose left form collides with an existing signature.
