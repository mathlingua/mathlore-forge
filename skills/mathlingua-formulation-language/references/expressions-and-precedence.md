# Expressions And Precedence

Expressions include arithmetic, calls, commands, grouped values, labels,
predicates, tuples, sets, and function literals.

```text
x + y * z
f(x, y)
(x + y)[:sum:]
\function:on{A}:to{B}(x)
x is? \set
```

From lowest to highest precedence: function literal `=>`; specifications and
predicates; infix commands; equality/special binary operators; addition;
multiplication; powers; named operators; unary prefix; postfix named operators;
atoms. Powers associate right. Arithmetic and named-operator chains associate
left. Infix commands bind more loosely than arithmetic; named operators bind
more tightly.

Use parentheses whenever a reader or formatter could plausibly misread the
intended grouping. Expression labels follow a grouped expression as `[:label:]`.

## Anti-patterns

- Do not assume rendered spacing defines precedence.
- Do not use a refined command expression in a general-expression position;
  only refined-capable statement contexts accept it.
- Do not label an ungrouped expression.
- Do not rely on a one-element tuple.
