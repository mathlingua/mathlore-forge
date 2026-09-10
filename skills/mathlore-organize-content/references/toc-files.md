# `toc` Files

Each nonempty line names one direct child `.mlg` file or directory:

```text
01_axioms.mlg
02_subsets.mlg -> Subsets
drafts -> HIDDEN
```

- Every direct `.mlg` file and directory appears exactly once.
- `/` and `\` are invalid because entries are direct child names.
- `name -> Display Title` overrides the navigation title.
- `name -> HIDDEN` keeps content in the collection but hides it from navigation;
  descendants inherit hidden state.
- Do not list `_preface_.mlg` or `toc` itself.
- Line order is display order. Preserve numeric prefixes and conceptual
  progression unless reorganization is the goal.

## Anti-patterns

- Do not add nested paths.
- Do not leave an unlisted direct child or a stale nonexistent entry.
- Do not list one child twice under different titles.
