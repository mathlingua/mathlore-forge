# `Topic:`

Use `Topic:` to register a documentation topic and relationships to other
topics or definition signatures.

```text
[#real.analysis]
Topic: "Limits, continuity, differentiation, and integration over the reals."
within: "#analysis"
Related:
. to: "\\real.sequence"
  specifies: "Sequences provide the first limit constructions."
Documented:
. called: "Real Analysis"
```

The `[#dotted.topic]` heading is required. `within:`, `Related: to:`, and
`specifies:` are quoted text. `Documented:` accepts only `called:`. Topic and
signature references are descriptive and need not resolve.

## Anti-patterns

- Do not use a command heading for a topic.
- Do not put ordinary documentation fields such as `written:` under a topic.
- Do not mistake a quoted signature for a command invocation.
