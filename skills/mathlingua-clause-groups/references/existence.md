# `exists:` And `existsUnique:`

For the semantic choice, read [`exists:`](exists.md) or
[`existsUnique:`](exists-unique.md).

Use `exists:` to bind a value whose optional `suchThat:` conditions hold. Use
`existsUnique:` when uniqueness is part of the intended assertion.

```text
. exists: y "in" Y
  suchThat:
  . f(x) = y

. existsUnique: e "in" M
  suchThat:
  . forAll: x "in" M
    then: e * x = x
```

The binding may be a declaration or specification accepted by the binding
parser. The symbol and `suchThat:` assumptions live only in the existential
child context.

## Anti-patterns

- Do not use the bound symbol outside the existential clause.
- Do not reuse a name already defined in an inherited scope.
- Do not choose `existsUnique:` unless uniqueness is genuinely part of the
  mathematics; parsing it does not prove uniqueness.
