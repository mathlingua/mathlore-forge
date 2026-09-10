---
name: mathlore-organize-content
description: Add, move, rename, order, hide, or retitle Mathlore chapters and pages by editing content directories, toc files, filenames, and _preface_.mlg overviews. Use for collection navigation and source organization, not ordinary edits within an existing mathematical item.
---

# Organize Mathlore Content

Keep source layout, navigation order, and chapter overviews consistent without
editing generated site output.

Start by inspecting the full `content/` tree, repository status, root `toc`,
nearest directory `toc`, and any `_preface_.mlg` in scope. Then read only the
reference matching the structural operation:

- [`toc` files](references/toc-files.md): direct children, ordering, display
  titles, and `HIDDEN`.
- [Pages and prefaces](references/pages-and-prefaces.md): navigable pages,
  directory overviews, naming, and placement.
- [Moves, renames, and splits](references/moves-renames-and-splits.md): preserve
  exposition, references, groups, and IDs.
- [Organization validation](references/validation.md): checks, formatter effects,
  and navigation review.

Preserve unrelated changes. Keep prerequisites before dependent exposition even
though command resolution is collection-wide. Do not edit generated `docs/`,
run `build.sh`, or force an export unless publishing is explicitly requested.
