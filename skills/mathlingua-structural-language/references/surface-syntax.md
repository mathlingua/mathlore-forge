# Surface Syntax

Use this reference when a group is parsed incorrectly or when adding headings,
sections, repeated arguments, comments, text, or multiline formulas.

## Rules

- An `.mlg` file is a sequence of top-level groups separated by blank lines.
- A heading such as `[\function:on{A}:to{B}]` belongs to the following group.
  The first section label, not the heading, determines the group kind.
- Section labels and order are case-sensitive: `Documented:` and `when:` are
  distinct spellings with fixed positions.
- Use an inline argument for one value or dot arguments for a repeated list:

```text
when: A is \set

when:
. A is \set
. x "in" A
```

- A dot argument is parsed two spaces deeper than its section. Nested section
  lines continue at the indentation used by nearby checked content.
- `--` starts a comment after leading whitespace. A blank line inside a group
  ends the current block; comments do not.
- Text arguments are double-quoted. Escapes are not interpreted. Single-quoted
  formulations are unsupported.
- A multiline formulation begins only when the entire opening line is `(`,
  `[`, `{`, or `(.` and ends with its matching delimiter at the same indent.
- A line whose first structural-looking colon follows a section-label-shaped
  prefix starts a nested group. Formulation operators such as `:=`, `:->`,
  `:=>`, and command tails such as `:to{B}` remain formulations.

## Anti-patterns

- Do not infer validity from visual alignment alone; run the formatter/checker.
- Do not insert a blank line between a section and its nested arguments.
- Do not lowercase `Documented:`, `Requires:`, or other capitalized labels.
- Do not put an arbitrary expression after `Title:` or `Text:`; those fields
  require quoted prose.
