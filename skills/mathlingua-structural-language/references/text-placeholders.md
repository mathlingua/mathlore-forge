# Text Placeholders

Use `TextTheorem:`, `TextAxiom:`, `TextConjecture:`, or `TextDefinition:` when
the reader-facing item should exist but a structured formulation is
intentionally deferred.

```text
TextTheorem: "Every finite-dimensional vector space has a basis."
Documented:
. called: "existence of a basis"
. description: "A prose placeholder pending structured formulation."
References:
. $linear.algebra.text
```

The body is quoted open text. Optional `Documented:` accepts only `called:`,
`written:`, `description:`, and `notes:`; `References:` may follow. The checker
adds `Id:` when omitted.

## Anti-patterns

- Do not use a text placeholder to hide a formulation error or bypass scope and
  requirement checks.
- Do not leave a mature, reusable concept opaque when it should become a
  structured definition or result.
- Do not claim that the checker validated the mathematics inside the prose.
