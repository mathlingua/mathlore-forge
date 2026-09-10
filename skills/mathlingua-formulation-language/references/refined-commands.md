# Refined Commands

Use a refined command to apply one or more adjective properties to a base type
or specification operator.

```text
\(continuous)::function:on{A}:to{B}
\(continuous, bounded)::function:on{A}:to{B}
A \:(proper)::subset:/ B
```

Refined command headings use the same parenthesized list. The refinement must be
defined by a matching `Refines:` group. Ordinary expression parsing does not
accept refined command expressions; use them in refined-capable statement
contexts such as theorem `given:` or expression-level `is?`.

Within a `Refines: specifies:` statement, `[[subject]]` denotes the enclosing
base type including parameters.

## Anti-patterns

- Do not invent an adjective without a `Refines:` definition.
- Do not use a refined command in a section parsed only as a general expression.
- Do not assume refinements with the same adjective on unrelated base commands
  are interchangeable.
- Do not use `[[subject]]` outside its refinement context.
