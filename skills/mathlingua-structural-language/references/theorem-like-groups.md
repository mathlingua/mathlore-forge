# Shared Theorem-Like Syntax

[`Axiom:`](axiom.md), [`Theorem:`](theorem.md), and
[`Conjecture:`](conjecture.md) share one structural shape. All require `then:`.

```text
Theorem:
given:
. X, Y is \set
. f is \function:on{X}:to{Y}
where:
. x "in" X
then:
. f(x) "in" Y
Documented:
. called: "functions map into their codomain"
```

Allowed order is the head, `given?`, `where?`, `then`, `iff?`, `Documented?`,
`Justification?`, `Aliases?`, `Writing?`, `References?`, `Metadata?`. A command
heading is optional. Put the result's human name in `Documented: called:`.

- `given:` introduces refined-capable declarations and facts.
- `where:` adds local assumptions available to `then:` and `iff:`.
- Use `is` in assumptions and `is?` for a type predicate in conclusions.
- The checker verifies scope, references, requirements, and known facts; it does
  not prove the conclusion.

## Anti-patterns

- Do not put text or a name after `Theorem:`; the head takes no argument.
- Do not weaken the claim or replace it with `\\anything` to satisfy the checker.
- Do not call an unproved statement a theorem merely because it parses.
- Do not introduce fresh conclusion symbols that were not bound in `given:`,
  `where:`, or a nested clause.
