# `Resource:`

Use `Resource:` to register a bibliographic source that `References:` sections
can cite.

```text
[$example.book]
Resource:
. title: "Example Book"
. author: "@ada.lovelace"
. publisher: "Example Press"
. year: "1843"
. url: "https://example.org/book"
```

The `[$dotted.resource]` heading is required. Available items include `title:`,
`author:`, `offset:`, `url:`, `homepage:`, `type:`, `edition:`, `editor:`,
`institution:`, `journal:`, `publisher:`, `volume:`, `month:`, `year:`, and
`description:`. Follow a nearby checked resource for field conventions. For a
PDF, `offset:` is the physical page where numbered page 1 appears.

## Anti-patterns

- Do not fabricate bibliographic fields or URLs.
- Do not duplicate an existing resource under another header.
- Do not confuse the `[$resource]` definition heading with a `$resource`
  citation under `References:`.
