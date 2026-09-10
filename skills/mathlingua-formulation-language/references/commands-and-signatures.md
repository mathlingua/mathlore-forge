# Commands And Signatures

Commands begin with `\` and name reusable mathematical concepts.

```text
\set
\function:on{A}:to{B}
\relation:from{A}:to{B}(x, y)
```

The signature removes concrete arguments while preserving path and tails:
`\function:on{A}:to{B}` has signature `\function:on:to`. Curly groups are
required where the defining heading expects them. Parenthesized groups invoke a
callable command; trailing invocation groups may be omitted only where the
definition permits.

Search the defining heading before every new use. Match tail order, curly-group
count and shape, optional tails, mapping specialization, variadics, and callable
groups. Builtin types use two leading backslashes in source, including
`\\type`, `\\statement`, `\\expression`, `\\specification`, `\\anything`, and
`\\abstract`.

## Anti-patterns

- Do not infer source arguments from rendered notation.
- Do not omit a required curly group or reorder command tails.
- Do not create two definitions with the same general signature unless valid
  mapping-parameter specialization distinguishes them.
- Do not use one leading slash for a builtin type.
