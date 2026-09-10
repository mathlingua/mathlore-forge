# `Conjecture:`

Use `Conjecture:` for a theorem-shaped claim explicitly not presented as
proved. Its syntax is the shared [theorem-like shape](theorem-like-groups.md).

```text
Conjecture:
given: n is \natural
then: \open.claim{n}
Documented:
. called: "example conjecture"
```

An optional `Justification:` may record evidence or rationale without claiming
a proof.

## Anti-patterns

- Do not use `Theorem:` for an open claim.
- Do not write supporting evidence as though it were a completed proof.
- Do not omit hypotheses needed to state the conjecture precisely.
