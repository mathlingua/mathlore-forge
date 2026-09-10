# How Do I Add A Property Or Adjective?

1. Find the exact base `Declares:` command and its target shape.
2. Read [`Refines:`](../../mathlingua-structural-language/references/refines.md)
   and [refined commands](../../mathlingua-formulation-language/references/refined-commands.md).
3. Use a refined heading, preserve the base target shape, state the defining
   facts/laws, and document with `adjective:`.

```text
[\(idempotent)::binary.operation:on{X}]
Refines: x_ * y_
when: X is \set
satisfies:
. forAll: x "in" X
  then: x * x = x
Documented:
. adjective: "idempotent"
```

If this merely restates an inherited refinement on a subtype, use
`implicitly:`; if it adds meaning, use `explicitly:`. Otherwise use neither.

## Do not

- Do not use `called:` instead of `adjective:`.
- Do not change the base target's structural shape.
- Do not use inheritance markers without checking their strict conditions.
- Do not define an adjective whose mathematical meaning is unrelated to the base.
