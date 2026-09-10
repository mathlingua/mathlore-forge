# Outline And Prose Groups

Use these heading-less top-level groups to structure reader-facing exposition.

```text
Title: "Functions"

SectionTitle: "Composition"

SubsectionTitle: "Associativity"

Text: "A function assigns each input exactly one output."
```

Each line is a separate top-level group and receives its own generated `Id:`.
Use `Title:` for the page title, section levels for visible subdivisions, and
`Text:` for Markdown prose with inline `$LaTeX$` when useful.

Read [narrative prose](../../mathlore-prose-content/references/narrative-prose.md)
before composing substantial text.

## Anti-patterns

- Do not wrap several outline groups into one block; blank lines separate them.
- Do not use `SectionTitle:` as a substitute for a navigable page title in
  `toc`.
- Do not put structured mathematical claims only in `Text:` when they should be
  searchable and checkable as definitions or results.
