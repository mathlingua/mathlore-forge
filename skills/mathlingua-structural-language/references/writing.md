# `Writing:` Groups And Sections

Use `Writing:` to alter how plain names render, without changing their meaning.
A top-level group applies collection-wide:

```text
Writing:
. "alpha :~> \alpha"
```

The body is a required double-quoted string containing a plain name, `:~>`, and
raw non-empty LaTeX. A definition-like item may also contain a local `Writing:`
section after `Aliases:` and before `References:`; local entries override global
ones only for that item.

Use [`Documented: written:`](../../mathlore-prose-content/references/rendering-templates.md)
for a command's mathematical notation. Use `Writing:` for otherwise plain
identifier rendering.

## Anti-patterns

- Do not omit the quotes; the right side is raw LaTeX, not a formulation.
- Do not use `Writing:` to create a command, establish a fact, or repair a bad
  signature.
- Do not add a global alias for a one-card rendering need.
