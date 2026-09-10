# How Do I Add, Move, Or Split A Page?

Read [project organization](../../mathlore-organize-content/SKILL.md) before
changing files or `toc`.

1. Inspect `content/toc`, the nearest directory `toc`, and `_preface_.mlg`.
2. Keep the numeric filename convention and place prerequisites before dependent
   exposition.
3. Add the direct child name exactly once to its parent's `toc`.
4. When moving or splitting, move complete groups with their existing IDs; do
   not copy them into both files.
5. Run a full collection check and inspect navigation order/title.

```text
03_new_topic.mlg -> New Topic
drafts -> HIDDEN
```

## Do not

- Do not list `_preface_.mlg` or `toc` inside `toc`.
- Do not use nested paths in a `toc` entry.
- Do not duplicate IDs while splitting.
- Do not edit generated `docs/` or run a forced export for routine organization.
