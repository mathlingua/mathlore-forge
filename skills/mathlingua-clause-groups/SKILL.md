---
name: mathlingua-clause-groups
description: Author or review nested MathLingua clause groups for logic, quantification, binding, conditionals, proof-style assertions, and piecewise definitions. Use for not, allOf, anyOf, oneOf, exists, existsUnique, forAll, let, if, have, piecewise, or equivalently blocks.
---

# MathLingua Clause Groups

Read only the reference for the clause being used:

- [`not`](references/not.md): negate one nested clause.
- [`allOf`](references/all-of.md): require every child clause.
- [`anyOf`](references/any-of.md): state alternatives.
- [`oneOf`](references/one-of.md): state one-of intent.
- [`exists`](references/exists.md): bind an existential value.
- [`existsUnique`](references/exists-unique.md): bind a uniquely existing value.
- [`forAll`](references/for-all.md): bind universal values and check a body.
- [`let`](references/let.md): introduce local values for a body.
- [`if`](references/if.md): conditional implication.
- [`have`](references/have.md): biconditional or proof-style assertion forms.
- [`piecewise`](references/piecewise.md): ordered conditional branches.
- [`equivalently`](references/equivalently.md): a biconditional chain.

Inline clauses are parsed first as declaration statements, then as expressions.
Bindings are local, processed in order, and may not shadow an inherited defined
symbol. Bind every symbol before it appears in a command or conclusion.
