# Names And Placeholders

Use ordinary names for bound values and stropped names when referring to an
operator as a value.

```text
x
x_1
X'
x'_a'
`*`
`*'_1`
```

Identifier-like names start with an ASCII letter or digit and may contain
internal underscores, subscripts, and trailing primes. Symbolic operator names
must be wrapped in backticks when used as names; `` `*`(a, b) `` invokes a bound
operator value.

Placeholders end in `_`; magnetic placeholders end in `__`:

```text
f(x_)
f(x__)
```

Ordinary placeholders describe forms. A magnetic placeholder is the special
single-input callable form used by mappings such as `f(x__)`. A function form
uses either one magnetic placeholder or one or more ordinary placeholders, not
both.

## Anti-patterns

- Do not use a bare operator character where the operator's value is intended.
- Do not mix `_` and `__` parameters in one function form.
- Do not assume a placeholder is a runtime wildcard; it binds a syntactic form.
- Do not use reserved exact names `is`, `is?`, or `via` as ordinary names.
