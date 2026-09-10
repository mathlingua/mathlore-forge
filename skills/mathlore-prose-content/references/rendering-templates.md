# Rendering Templates

A documented template substitutes a heading/form parameter by appending `?`:

```text
. called: "function from $A?$ to $B?$"
. written: "A? \rightarrow B?"
```

For a source placeholder such as `n_`, both `n_?` and normalized `n?` match.
Use the clearer spelling and follow nearby style.

- `A?` preserves the rendered value.
- `A+?` ensures one outer pair of parentheses for a compound value.
- `A-?` removes outer wrapping parentheses.
- `@[M]{ in $M?$}` is included only when substitution `M` is available.

Mapping definitions may provide invocation and mapping-form templates:

```text
Documented:
. writing: x(i)
  as: "x?_{i?}"
. writing: x(i_)
  as: "\left\{x?\right\}_{i_?=1}^{\infty}"
```

The `writing:` target must match the declared mapping exactly, with placeholders
or their ordinary names. `as:` is raw LaTeX.

## Anti-patterns

- Do not reference a template key absent from the heading or form.
- Do not copy parenthesis modifiers without checking the desired grouping.
- Do not use a declaration alias in a mapping template when the mapping itself
  has a different name.
- Do not expect raw template text to be semantically reference-checked.
