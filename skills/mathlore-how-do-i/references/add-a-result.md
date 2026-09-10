# How Do I Add An Axiom, Theorem, Or Conjecture?

1. Choose the epistemically correct head: assumed `Axiom:`, established
   `Theorem:`, or unproved `Conjecture:`.
2. Read [theorem-like groups](../../mathlingua-structural-language/references/theorem-like-groups.md)
   and the needed [clause references](../../mathlingua-clause-groups/SKILL.md).
3. Put declarations/facts in `given:`, additional assumptions in `where:`, and
   the assertion in required `then:`.

```text
Theorem:
given:
. X is \set
where:
. x "in" X
then:
. x is? \\anything
Documented:
. called: "example result"
```

Check scope and command requirements, then independently review whether the
statement is mathematically correct and appropriately sourced.

## Do not

- Do not put the theorem's name after `Theorem:`.
- Do not write `is` where a conclusion requires `is?`.
- Do not introduce a fresh symbol only in `then:`.
- Do not relabel a conjecture as a theorem because the checker accepts it.
