# `Person:`

Use `Person:` to register a named person for resource authorship or historical
metadata.

```text
[@ada.lovelace]
Person: "Ada Lovelace"
biography: "English mathematician and writer."
```

The `[@dotted.name]` author heading is required. `Person:` accepts one or more
quoted prose arguments; `biography:` is optional quoted prose. Search for an
existing person header before adding one.

## Anti-patterns

- Do not use a command or resource heading.
- Do not invent biographical details.
- Do not create spelling variants of an existing author identity.
