# `Disambiguates:`

Use `Disambiguates:` when one function or operator form should select among
expressions according to ordered conditions, with an optional fallback.

```text
[f(x_)]
Disambiguates:
when: x is \natural
to: \natural.case{x}
when: x is \real
to: \real.case{x}
else: \generic.case{x}
Documented:
. called: "disambiguated $f?$."
```

The heading is required and must be a function or operator form. Supply at
least one `when:`/`to:` pair or `else:`. Each `when:` belongs to the immediately
following `to:`. Later optional sections are `Documented:`, `Justification:`,
`Aliases:`, `Writing:`, `References:`, and `Metadata:` in that order.

## Anti-patterns

- Do not separate a `when:` from its `to:` or put `else:` before a pair.
- Do not use this group merely to define a piecewise mathematical value; use a
  `Defines:` `expresses:` [piecewise clause](../../mathlingua-clause-groups/references/piecewise.md).
- Do not assume overlapping branches are automatically mathematically exclusive.
