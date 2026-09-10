---
name: mathlore-author-content
description: Route any request to create or update MathLingua (.mlg) mathematical or narrative content in the Mathlore collection to the smallest relevant authoring guidance. Use for definitions, structures, refinements, statements, results, prose, notation, citations, or edits under content/. Do not use for MathLingua compiler implementation.
---

# Author Mathlore Content

Use this skill as the entry point. Start here, choose the narrowest route below,
and read only that linked skill or reference. Follow a nested link only when the
edit actually uses that construct.

## Before any edit

1. Confirm the Mathlore root contains `mlg.json` and `content/`.
2. Read the complete target page, its nearest `toc`, and nearby definitions.
3. Search all `content/**/*.mlg` for the concept, command path, signature, and
   notation before creating anything new.
4. Preserve the mathematics and unrelated user changes. Edit source under
   `content/`; do not hand-edit generated `docs/`.
5. For a new top-level item, omit `Id:`. Let `mlg check` generate a UUID, then
   inspect and retain it. Never copy an existing ID.

## Choose a route

- [How do I...?](../mathlore-how-do-i/SKILL.md) maps authoring goals to focused
  recipes, examples, and anti-patterns. Use it when the desired outcome is
  clearer than the required syntax.
- [Prose and rendering](../mathlore-prose-content/SKILL.md) covers `Text:`,
  narrative style, `Documented:`, templates, code fences, and citations.
- [Project structure](../mathlore-organize-content/SKILL.md) covers pages,
  chapters, `toc`, `_preface_.mlg`, ordering, hiding, moving, and splitting.
- [Structural language](../mathlingua-structural-language/SKILL.md) covers the
  line-oriented groups and sections that organize an `.mlg` document.
- [Formulation language](../mathlingua-formulation-language/SKILL.md) covers the
  mathematical expressions inside structural sections.
- [Clause groups](../mathlingua-clause-groups/SKILL.md) covers logic,
  quantification, local binding, conditionals, and piecewise clauses.
- [Support sections](../mathlingua-support-sections/SKILL.md) covers
  `Requires:`, `Enables:`, documentation, aliases, references, metadata, and
  definition-body sections.
- [Diagnosis](../mathlore-diagnose-content/SKILL.md) covers checker, scope,
  semantic, formatting, ID, and rendering failures.

## Structural language at a glance

- [Surface syntax](../mathlingua-structural-language/references/surface-syntax.md)
  — lines, indentation, headings, section arguments, comments, and multiline
  formulations; consult whenever layout or parsing boundaries matter.
- [Outline and prose groups](../mathlingua-structural-language/references/outline-and-prose-groups.md)
  — `Title:`, `SectionTitle:`, `SubsectionTitle:`, and `Text:`; use to organize
  exposition.
- [`Writing:`](../mathlingua-structural-language/references/writing.md) — global
  or item-local plain-name-to-LaTeX aliases; use for rendering only.
- [`Disambiguates:`](../mathlingua-structural-language/references/disambiguates.md)
  — choose one rendering/value by ordered conditions.
- [`Declares:`](../mathlingua-structural-language/references/declares.md) — define
  a reusable type, interface, relation shape, or statement shape.
- [`Defines:`](../mathlingua-structural-language/references/defines.md) — define
  a concrete or intentionally abstract value or operation.
- [`Realizes:`](../mathlingua-structural-language/references/realizes.md) — fill
  every open component of an `abstractly:` definition.
- [`Refines:`](../mathlingua-structural-language/references/refines.md) — attach
  an adjective/property to an existing type or specification operator.
- [`States:`](../mathlingua-structural-language/references/states.md) — define a
  reusable command-backed proposition.
- [`Axiom:`](../mathlingua-structural-language/references/axiom.md),
  [`Theorem:`](../mathlingua-structural-language/references/theorem.md), and
  [`Conjecture:`](../mathlingua-structural-language/references/conjecture.md) —
  assert assumed, established, or explicitly unproved mathematical results.
- [`Relation:`](../mathlingua-structural-language/references/relation.md) — record
  a checked or prose relationship between concepts, topics, or definitions.
- [`Equivalent:`](../mathlingua-structural-language/references/equivalent.md) —
  make compatible command definitions interchangeable.
- [`Topic:`](../mathlingua-structural-language/references/topic.md) — declare a
  documentation topic and related-topic metadata.
- [`Person:`](../mathlingua-structural-language/references/person.md) and
  [`Resource:`](../mathlingua-structural-language/references/resource.md) —
  register authors and bibliographic resources.
- [`Specify:`](../mathlingua-structural-language/references/specify.md) — set the
  collection's numeric-literal and variadic-index fallback types.
- [Text placeholders](../mathlingua-structural-language/references/text-placeholders.md)
  — prose-only theorem, axiom, conjecture, or definition cards when a structured
  formulation is intentionally deferred.

## Formulation language at a glance

- [Names and placeholders](../mathlingua-formulation-language/references/names-and-placeholders.md)
  — identifiers, stropped operators, `_`, and `__` bindable forms.
- [Forms and declarations](../mathlingua-formulation-language/references/forms-and-declarations.md)
  — describe reusable shapes and introduce their symbols with `::=`.
- [Expressions and precedence](../mathlingua-formulation-language/references/expressions-and-precedence.md)
  — arithmetic, application, grouping, labels, and binding order.
- [Statements and specifications](../mathlingua-formulation-language/references/statements-and-specifications.md)
  — `is`, `is?`, quoted specs, `:=`, `via`, and statement-position rules.
- [Commands and signatures](../mathlingua-formulation-language/references/commands-and-signatures.md)
  — command uses, tails, curly arguments, invocation groups, and signature
  matching.
- [Command headers](../mathlingua-formulation-language/references/command-headers.md)
  — declare ordinary, callable, optional-tail, infix, and spec-infix commands.
- [Refined commands](../mathlingua-formulation-language/references/refined-commands.md)
  — `\(adjective)::base` types and refined specification operators.
- [Operators and member access](../mathlingua-formulation-language/references/operators-and-members.md)
  — named operators, infix commands, bound members, and direct command
  components.
- [Tuples, sets, and functions](../mathlingua-formulation-language/references/tuples-sets-and-functions.md)
  — collection literals, set builders, function literals, and calls.
- [Variadics and slices](../mathlingua-formulation-language/references/variadics-and-slices.md)
  — one- and two-dimensional variable-length arguments and broadcasts.
- [Mapping parameters](../mathlingua-formulation-language/references/mapping-parameters.md)
  — mapping-literal calls and specialized parameter-selector signatures.
- [Aliases and capability arrows](../mathlingua-formulation-language/references/aliases-and-capabilities.md)
  — `:=>`, `:->`, `:<->:`, and capability reductions.
- [Headers and labels](../mathlingua-formulation-language/references/headers-and-labels.md)
  — command, topic, author, resource, and local justification headings.
- [Build expressions](../mathlingua-formulation-language/references/build-expressions.md)
  — construct a value at a type using `\type@value`.
- [Specification literals](../mathlingua-formulation-language/references/spec-literals.md)
  — anonymous-subject specifications and structural type literals.
- [Command contexts](../mathlingua-formulation-language/references/command-contexts.md)
  — inline `#using`/`#given` values and inferred `X?` parameters.
- [Builtin command expressions](../mathlingua-formulation-language/references/builtin-command-expressions.md)
  — double-slash builtin value forms with semicolon-separated arguments.

## Validation boundary

Use the first available checker from the Mathlore root: `mlg check`,
`../mathlingua/target/debug/mlg check`, or
`cargo run --manifest-path ../mathlingua/Cargo.toml -- check`. A path after
`check` filters diagnostics during iteration, but finish with an unfiltered full
collection check. Review formatter and generated-ID changes. A clean check
confirms well-formedness and tracked facts; it does not prove the mathematics.

When behavior remains uncertain, consult `../mathlingua/docs/language.md`, then
the focused `structural_syntax.md` or `formulation_syntax.md`. The running
checker is the final authority for the installed version.
