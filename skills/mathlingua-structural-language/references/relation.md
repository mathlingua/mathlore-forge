# `Relation:`

Use `Relation:` for a standalone bidirectional relationship between two
concepts, topics, or definition signatures. It has no heading.

```text
Relation: "connects two presentations"
between: "#linear.algebra"
and: "\\vector.space"
specifies: "The topic develops the referenced definition."
Documented:
. called: "topic-definition relationship"
```

Each subject is either an unquoted declaration such as `a is \real`, a quoted
topic reference such as `"#real.analysis"`, or a quoted command signature such
as `"\\function:on:to"`. `specifies:` may be a checked clause or quoted prose.

Order is `Relation`, `using?`, required `between`, required `and`, `when?`,
`specifies?`, then documentation and standard trailing support sections.

## Anti-patterns

- Do not add a heading; `Relation:` is heading-less.
- Do not write a full command invocation when a quoted definition signature is
  intended.
- Do not assume quoted references are existence-checked or mathematically
  proven; they are recorded as prose relationships.
