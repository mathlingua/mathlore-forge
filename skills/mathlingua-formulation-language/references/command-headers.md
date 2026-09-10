# Command Headers

Use a square-bracket heading to define a command signature and bind its
parameters for the following top-level group.

```text
[\function:on{A}:to{B}]
[\natural.succ(n_)]
[n_ \.natural.+./ m_]
[A \:subset:/ B]
```

Curly arguments are part of the command shape; placeholder-style trailing
parameters bind callable inputs. An optional tail uses `:?` only in a declaration
heading:

```text
[\function:on{A}:?to{B}]
```

This accepts references with or without `:to`, while preserving the heading's
tail order. Infix command headings use `\.` and `./`; specification-infix
headings use `\:` and `:/`.

Header parameters are in scope for the group and normally need type/spec facts
in `when:`.

## Anti-patterns

- Do not write `:?` at a command use site.
- Do not treat the heading as choosing the group kind.
- Do not redeclare heading parameters under `using:`.
- Do not add a signature that duplicates an existing definition.
