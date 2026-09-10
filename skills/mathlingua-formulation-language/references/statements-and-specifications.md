# Statements And Specifications

Use these forms according to whether a section establishes a fact, binds a
value, or asserts a predicate.

```text
x is \set
x_, y_ is \set
x "in" A
x := y
x is? \set
X is \magma via (A, *)
```

- `is` establishes a type fact in declaration, assumption, or specification
  positions. The helper form requires spaces around ` is `.
- `is?` is a type predicate used in expression/conclusion positions.
- A quoted specification such as `x "in" A` establishes or asserts a relation
  according to its containing section.
- `:=` assigns or binds a value. Names used only on its right must already be
  in scope.
- `via` records the structural form through which a type extends another.
- Specification literals and spec-infix operators are distinct from ordinary
  equality expressions; use the syntax defined by their headings.

Assumptions are processed in order. A conclusion cannot introduce a fresh
symbol.

## Anti-patterns

- Do not use `is` in `then:` when a predicate `is?` is required.
- Do not use `is?` to bind or establish a type in `when:` or `given:`.
- Do not place an undeclared symbol on the right of `:=`.
- Do not assume all quoted-operator text accepted by a statement helper is also
  accepted by the general expression parser.
