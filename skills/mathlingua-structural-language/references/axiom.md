# `Axiom:`

Use `Axiom:` for a foundational statement intentionally assumed rather than
derived within the development. Its syntax is the shared
[theorem-like shape](theorem-like-groups.md).

```text
Axiom:
given: X is \set
then: \choice.principle{X}
Documented:
. called: "choice principle"
```

## Anti-patterns

- Do not label an ordinary proved consequence as an axiom.
- Do not put the axiom's name after `Axiom:`; use `Documented: called:`.
- Do not assume the checker proves consistency or independence.
