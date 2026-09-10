# `Enables:`

Use `Enables:` for operations, casts, or views supplied by a construct beyond
its defining requirements.

```text
Enables:
. capability: x_ "in" X :-> x_ is \element
. from: Y is \subtype
  capability: y_ "in" Y :-> y_ "in" X
. view:
  as: S := X is \set
```

Accepted items are `capability:`, `from:` plus `capability:`, `from:` plus `as:`,
and `view:` plus `as:`. A member capability such as `x.inv` or `x.f(a_)` must
use the described subject as owner. Although `Requires:` and `Enables:`
capabilities are combined during checking, keep the communicative distinction:
needed by definition versus additionally provided.

## Anti-patterns

- Do not use an unrelated owner in a member capability.
- Do not encode a cast or view as prose documentation.
- Do not claim a capability whose target cannot be established from the
  construct's facts.
