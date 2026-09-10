# How Do I Add A Value Or Operation?

1. Search for the intended command and every command used in its body.
2. Read [`Defines:`](../../mathlingua-structural-language/references/defines.md),
   [statements](../../mathlingua-formulation-language/references/statements-and-specifications.md),
   and [`expresses:`](../../mathlingua-support-sections/references/expresses.md).
3. State an explicit type, ordered parameter requirements, and the value/body.

```text
[\identity:on{A}]
Defines: f(x__) is \function:on{A}:to{A}
when: A is \set
expresses: f(x__) := x__
Documented:
. called: "identity function on $A?$"
. written: "\\operatorname{id}_{A?}"
```

For a structured concrete object, give every component exactly one value. If
open parts are intentional, use `abstractly:` and plan a `Realizes:` item.

## Do not

- Do not omit the defined value's type.
- Do not leave a concrete component typed but valueless.
- Do not use `abstractly:` as an escape hatch.
- Do not write direct component source with one dot.
