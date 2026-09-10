---
name: mathlingua-structural-language
description: Author or review MathLingua's line-oriented document structure, top-level groups, section order, indentation, and structural constructs in Mathlore .mlg files. Use when choosing or shaping a group such as Declares, Defines, Refines, States, Theorem, Relation, Topic, or Resource. Do not use for expression grammar alone.
---

# MathLingua Structural Language

Read only the reference for the construct being edited. If the problem is the
formula inside a section, switch to
[formulation language](../mathlingua-formulation-language/SKILL.md). If it is a
nested logical block, switch to [clause groups](../mathlingua-clause-groups/SKILL.md).

## Surface and narrative

- [Surface syntax](references/surface-syntax.md): lines, indentation, headings,
  arguments, comments, blank lines, quoted text, and multiline formulations.
- [Outline and prose groups](references/outline-and-prose-groups.md): `Title:`,
  `SectionTitle:`, `SubsectionTitle:`, and `Text:`.
- [`Writing:`](references/writing.md): collection-wide and item-local rendering
  aliases.

## Definition and assertion groups

- [`Disambiguates:`](references/disambiguates.md): conditional selection.
- [`Declares:`](references/declares.md): reusable types and interfaces.
- [`Defines:`](references/defines.md): values and operations.
- [`Realizes:`](references/realizes.md): implementations of abstract definitions.
- [`Refines:`](references/refines.md): adjective/property refinements.
- [`States:`](references/states.md): reusable propositions.
- [`Axiom:`](references/axiom.md): assumed foundational results.
- [`Theorem:`](references/theorem.md): claimed established results.
- [`Conjecture:`](references/conjecture.md): explicitly unproved results.
- [Shared theorem-like syntax](references/theorem-like-groups.md): section order,
  scope, and assertion rules common to all three.

## Knowledge and metadata groups

- [`Relation:`](references/relation.md): relationships between subjects.
- [`Equivalent:`](references/equivalent.md): interchangeable commands.
- [`Topic:`](references/topic.md): documentation topics.
- [`Person:`](references/person.md): named authors or people.
- [`Resource:`](references/resource.md): bibliographic records.
- [`Specify:`](references/specify.md): numeric-literal fallback types.
- [Text placeholders](references/text-placeholders.md): prose-only result and
  definition cards.

## Sections inside groups

- [Support sections](../mathlingua-support-sections/SKILL.md): `using:`, `when:`,
  `extends:`, `specifies:`, `satisfies:`, `expresses:`, `Requires:`, `Enables:`,
  `Documented:`, `Justification:`, `Aliases:`, `References:`, and metadata.
- [Clause groups](../mathlingua-clause-groups/SKILL.md): nested logic accepted
  by `when:`, `that:`, `then:`, `satisfies:`, and similar sections.

Keep capitalization and section order exact. The first section label—not the
heading—selects the group kind.
