# `Metadata:` And `Id:`

`Metadata:` accepts nested `id:` and `version:` values where supported. Most
Mathlore top-level content instead receives a singular trailing `Id:` section
from the checker.

For a new top-level item:

1. Omit `Id:` while authoring.
2. Run `mlg check` from the collection root.
3. Keep the generated UUID and inspect all formatter changes.

When moving an existing complete group, keep its ID with it. When splitting or
copying, each resulting top-level item needs its own unique ID.

## Anti-patterns

- Never copy an existing ID into a new group.
- Do not use placeholder UUIDs.
- Do not hand-edit IDs to make two copies appear related.
- Do not place metadata outside the exact order accepted by the parent group.
