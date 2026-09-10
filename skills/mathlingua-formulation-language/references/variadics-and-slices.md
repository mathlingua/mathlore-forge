# Variadics And Slices

Use variadics only in curly command argument groups. Common one-dimensional
forms are:

```text
x...
x...n
x[i_ := 0...n]
x[i_ := 1...n]
```

The whole `{...}` group is variadic. Bracketed forms bind an index and optional
length, starting only at 0 or 1. Reusing a length name across groups constrains
equal lengths. Refer to elements as `x[i]` and slices as `x[1...i_...n]`.
Slices broadcast on the left of `:=`, `=`, `!=`, `is`, `is?`, and quoted specs;
paired slices must spell the same range exactly.

Two-dimensional curly variadics declare a rectangle:

```text
x[(i_, j_) := (1,1)...(m,n)]
```

Calls use comma-separated columns and semicolon-separated rows. Rows must be
nonempty and equal width. Select with forms such as `x[a...b, c...d]`,
`x[a, ...]`, or `x[..., c]`.

## Anti-patterns

- Do not use variadics in parentheses or mix them with other values in one
  curly group.
- Do not start an indexed range anywhere except 0 or 1.
- Do not pair slices with different range spelling.
- Do not pass a flat list to a two-dimensional parameter.
- Do not confuse magnetic `x__` with a spreading curly variadic.
