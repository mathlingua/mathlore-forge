# How Do I Choose The Right Construct?

Choose by the semantic role of the new content:

| Goal | Construct |
|---|---|
| Explain or connect existing mathematics | `Text:` |
| Introduce a reusable type/interface and facts every instance carries | `Declares:` |
| Introduce a concrete value, operation, or callable body | `Defines:` |
| Supply the open parts of an `abstractly:` definition | `Realizes:` |
| Add an adjective/property to an existing type or spec operator | `Refines:` |
| Define a reusable command-backed proposition | `States:` |
| Assert a standalone assumed/proved/unproved result | `Axiom:`, `Theorem:`, `Conjecture:` |
| Publish an intentionally prose-only definition or result for now | `TextDefinition:` or another text placeholder |

Before choosing, search the entire collection. An existing command may only need
new prose, notation, a refinement, or a theorem rather than a duplicate
definition.

## Anti-patterns

- Do not use `Defines:` for an interface with no value.
- Do not use `Declares:` for a concrete object.
- Do not use `States:` for a one-off theorem.
- Do not use a text placeholder to bypass a formulation error.
- Do not create a new command merely to rename an existing concept.
