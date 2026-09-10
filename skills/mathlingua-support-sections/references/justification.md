# `Justification:`

Use `Justification:` after `Documented:` for labeled `have:` entries that
support labeled formulations elsewhere in the same group.

```text
satisfies:
. (. x = z .)[:transitive:]
Documented:
. called: "example"
Justification:
. [transitive]
  have: x = z
  asserting: x = y
  because: y = z
```

Every entry requires a `[label]` heading. Its `have:` must restate the matching
labeled formulation. `asserting:` is optional; absent it, surrounding facts are
used. Every justification entry must be referenced by a formulation label.

## Anti-patterns

- Do not create an unlabeled entry or an entry whose label is never referenced.
- Do not make `have:` differ from the labeled formulation.
- Do not put `Justification:` before `Documented:`.
- Do not treat this section as unchecked proof prose.
