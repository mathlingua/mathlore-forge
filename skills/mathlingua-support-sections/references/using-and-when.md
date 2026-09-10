# `using:` And `when:`

Use `using:` to introduce auxiliary local symbols needed by a definition. Use
`when:` to state ordered requirements and assumptions for heading parameters.

```text
[\construction:of{A}]
Defines: Y is \set
using: B is \set
when:
. A is \set
. B \:subset:/ A
```

Symbols and facts are processed in source order. A command may be used only
after its argument symbols and required facts are available. Header parameters
normally need matching `when:` facts; the target symbol being described is the
usual exception.

## Anti-patterns

- Do not redeclare a heading parameter or target symbol in `using:`.
- Do not add a `when:` fact for a symbol that is not a parameter or previously
  introduced auxiliary.
- Do not reference a symbol in an earlier assumption before declaring it.
- Do not weaken requirements solely to satisfy the checker.
