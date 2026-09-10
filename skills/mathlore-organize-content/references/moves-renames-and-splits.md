# Moves, Renames, And Splits

Before moving content, inspect incoming and outgoing command references and the
expository prerequisites around it.

- Move complete top-level groups with their existing IDs.
- When splitting, remove each moved group from the old file; never duplicate it.
- Update only the moved file/directory's parent `toc`. Nested `toc` entries still
  refer to their own direct children.
- Preserve source order where later prose relies on earlier definitions.
- Search for prose links or resource references that mention old locations or
  titles.

## Anti-patterns

- Do not copy a group and leave both copies with the same ID or signature.
- Do not move prerequisites after dependent exposition without a deliberate
  reason.
- Do not rename generated `docs/` output instead of source content.
