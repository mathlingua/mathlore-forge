# Mapping Parameters And Specialized Signatures

Use mapping-parameter selectors when a command operates with respect to chosen
parameters of a mapping.

```text
[\integral{f(x_, y_)}:d{f.x_}]
[\integral{f(x_, y_)}:d{f.u?_, f.v?_}]
```

An exact selector names a declared parameter (`f.x_`). An arbitrary selector
uses a fresh name with `?_` (`f.u?_`). At the use site, bind mapping parameters
explicitly:

```text
\integral[x_, y_ is \real]{x_^2 + y_^2}:d{x_}
```

All selectors must occupy exactly one curly group, share one owner, and point to
a mapping declared in exactly one other curly group. Selected values at a use
site must be parameters of that mapping. Ranged mappings may select a fixed
number of arbitrary parameters or a variadic subset.

These headings have specialized signatures (`#1`, `#?`, `#*`) in addition to a
general signature. Resolution prefers fixed arity, then exact positions, then
arbitrary positions, then variadic subsets.

## Anti-patterns

- Do not use an arbitrary selector name that duplicates a declared mapping
  parameter.
- Do not mix selector owners or spread selectors across curly groups.
- Do not select an unrelated use-site value.
- Do not use mapping selectors in infix or refined headings.
