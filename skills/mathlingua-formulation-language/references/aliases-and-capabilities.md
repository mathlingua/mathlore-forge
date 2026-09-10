# Aliases And Capability Arrows

Use `:=>` for expression aliases:

```text
alias: f(x_) :=> x_ + x_
```

The left side may be a form/declaration or an ordinary/infix command header;
the right side is an expression.

Use `:->` for one-way specification implication and `:<->:` for equivalence:

```text
capability: x_ "in" R :-> x_ is \real
capability: x_ "in" S :<->: x_ is \integer
capability: x_ "in" X :-> \\abstract
```

Multiple conclusions may be separated by semicolons. `:<->:` reverses only when
every conclusion is available. Capabilities owned by a `Declares:` type apply
to every instance; capabilities owned by `Defines:` or `Realizes:` apply to
that defined command value and its substituted parameters.

Collection/local rendering aliases use the separate quoted `:~>` syntax and do
not establish semantic reductions.

## Anti-patterns

- Do not expect reverse inference from `:->`.
- Do not use a refined command header on an expression-alias left side.
- Do not confuse `:=>` aliases with function literals using `=>`.
- Do not use `:~>` where a semantic capability is required.
