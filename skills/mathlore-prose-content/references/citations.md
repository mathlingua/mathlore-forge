# Citations

Use `References:` with an existing resource header when a claim, attribution,
or historical statement benefits from a source.

```text
References:
. $example.book
. $example.paper:page{12}
```

Search `content/**/*.mlg` for the source before adding one. If absent, add a
[`Resource:`](../../mathlingua-structural-language/references/resource.md) only
from reliable bibliographic details supplied by the user or an authoritative
source. Add a [`Person:`](../../mathlingua-structural-language/references/person.md)
only when its reusable author identity is needed.

For PDFs, `:page{n}` means the document's numbered page; the resolved physical
page incorporates the resource's `offset:`.

## Anti-patterns

- Do not fabricate titles, authors, dates, URLs, or page numbers.
- Do not add a duplicate resource under a slightly different key.
- Do not cite a source that does not support the nearby claim.
- Do not confuse a web page's display title with verified bibliographic data.
