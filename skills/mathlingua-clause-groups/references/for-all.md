# `forAll:`

Use `forAll:` to bind one or more universally quantified values, add optional
local assumptions in `where:`, and check required `then:` clauses.

```text
. forAll: x, y is \element.of{G}
  where: x != y
  then:
  . x * y "in" G
```

Bindings and `where:` facts are available only inside `then:`. If an input type
or command has requirements, establish them before use and in source order.

## Anti-patterns

- Do not omit `then:`.
- Do not bind a symbol with the same name as one already defined outside.
- Do not use a quantifier solely to smuggle an undeclared conclusion symbol
  into a broader scope.
