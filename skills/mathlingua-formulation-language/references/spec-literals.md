# Specification And Structural Type Literals

A specification literal is a `\\specification` value with anonymous subject
`_`:

```text
_ is \set
_ "in" X
```

Apply a spec literal to a subject with `satisfies`. Structural type literals use
a complete specification at every leaf:

```text
(_ is \natural, _ "in" \reals)
{_ is \natural : ...}
(_ is \natural) -> (_ "in" \naturals)
(_ is \natural, _ "in" \reals) -> (_ is \real)
```

The function-type arrow `->` takes one or more parenthesized input specs and
exactly one parenthesized output spec. Function values use `=>` instead. Each
anonymous `_` is instantiated by the matching component or argument.

## Anti-patterns

- Do not write raw nominal tuple types such as `(\natural, \real)`; write a spec
  at each leaf.
- Do not use a named subject where a spec literal requires `_`.
- Do not confuse function type `->` with function literal `=>`.
- Do not omit parentheses around function-type input and output specs.
