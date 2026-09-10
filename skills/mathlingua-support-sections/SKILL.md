---
name: mathlingua-support-sections
description: Author or review MathLingua sections nested within definition and result groups, including context, specifications, requirements, capabilities, documentation, justification, aliases, writing, references, and metadata. Use when the top-level group is known but one of its supporting sections needs detail.
---

# MathLingua Support Sections

Read only the section reference needed by the current group:

- [`using:` and `when:`](references/using-and-when.md): auxiliary symbols and
  ordered requirements.
- [`extends:`](references/extends.md): declare subtyping for a `Declares:` type.
- [`specifies:`](references/specifies.md): facts or component values carried by
  the construct.
- [`satisfies:`](references/satisfies.md): proposition clauses required of a
  declared or refined object.
- [`expresses:`](references/expresses.md): body defining a value or callable
  component.
- [`Requires:`](references/requires.md): notation or definitions needed by the
  construct.
- [`Enables:`](references/enables.md): capabilities, casts, and views supplied
  by the construct.
- [`Documented:`](references/documented.md): reader-facing names, notation, and
  descriptions.
- [`Justification:`](references/justification.md): labeled `have:` entries.
- [`Aliases:`](references/aliases.md): item-owned expression or spec aliases.
- [Local `Writing:`](references/local-writing.md): item-scoped rendering aliases.
- [`References:`](references/references.md): links to registered resources.
- [`Metadata:` and `Id:`](references/metadata-and-id.md): versions and identity.

Not every top-level group accepts every section. Check the parent construct's
reference first and preserve its exact section order.
