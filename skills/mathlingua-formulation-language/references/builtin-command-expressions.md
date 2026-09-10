# Builtin Command Expressions

Builtin value forms use two leading backslashes and semicolon-separated
specification/predicate arguments:

```text
\\allOf{P; Q}
\\forAll{x "in" X}:then{P(x)}
\\piecewise{x < 0}:then{-x}:else{x}
```

They are distinct from builtin type names such as `\\statement` and from
single-slash user-defined commands. Builtin clause commands mirror structural
clause groups and enforce their own argument and required-tail shapes.

## Anti-patterns

- Do not comma-separate builtin clause arguments; use semicolons.
- Do not omit a required builtin tail such as `:then`.
- Do not use one slash for a builtin or two for an ordinary command.
- Do not assume every structural section label has a builtin command form.
