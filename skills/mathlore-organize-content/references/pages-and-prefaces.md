# Pages And Prefaces

Use a normal `.mlg` file plus a matching parent `toc` entry for a navigable page.
Use `_preface_.mlg` for a directory overview; it renders at the directory root
and is not itself a navigation entry.

Choose the narrowest existing page that fits the concept. Create a new page only
when the material forms a distinct topic or would make an existing page
unwieldy. Follow local numeric filenames, title style, and prose/structured-card
balance.

New top-level groups may omit `Id:` until the checker generates one.

## Anti-patterns

- Do not create a page solely to avoid understanding a nearby page.
- Do not list `_preface_.mlg` in `toc`.
- Do not rely on filename order; `toc` controls display order.
