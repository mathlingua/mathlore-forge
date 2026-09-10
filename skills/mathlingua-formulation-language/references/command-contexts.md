# Command Contexts And Inferred Parameters

A command use may supply its definition's local context inline with one suffix:

```text
\construction{A}#using{B := C; x is \set}
\result{A}#given{x "in" A; P}
```

`#using{...}` and `#given{...}` accept semicolon-separated assignments,
declaration statements, expressions, or raw context text according to the
command's declared context. Match parameter names and requirements from the
definition; use only one context suffix at the end of the command expression.

An inferred command argument is written `X?`. Its first occurrence introduces
`X` with the type required by that argument position; later references use
plain `X`.

## Anti-patterns

- Do not invent context parameter names without reading the command definition.
- Do not place a context suffix before command tails or invocation groups.
- Do not expect context values to escape the command expression.
- Do not repeat `?` on later uses of an inferred parameter.
