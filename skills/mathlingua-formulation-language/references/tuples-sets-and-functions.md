# Tuples, Sets, And Functions

Use ordinary composite expression forms for tuples, set literals/builders,
function calls, and function literals.

```text
(x, y)
{x, y, z}
{x_ : x_ "in" A | x_ != 0}
f(x, y)
(x_ is \real) => x_ + 1
```

Tuple forms and tuple expressions require at least two elements. Set-builder
bindings are local to their condition/body. Function calls must match the
callable shape of the referenced value or command. Subset selection is narrow:
`x[i]`, `x[i, j]`, and `x[i[j]]` accept names in brackets, not arbitrary
expressions.

## Anti-patterns

- Do not write a one-element tuple.
- Do not use an unbound set-builder placeholder in the predicate or output.
- Do not infer call arity from a `written:` template.
- Do not put arbitrary arithmetic inside subset-selection brackets.
