# `References:`

Use `References:` to cite resources already registered by `[$resource]`
headings.

```text
References:
. $example.book
. $example.paper:page{12}
```

Search the collection before adding a resource. A PDF page citation uses the
resource's configured `offset:` when producing its physical link. See
[citations](../../mathlore-prose-content/references/citations.md) for authoring
workflow and [`Resource:`](../../mathlingua-structural-language/references/resource.md)
for bibliographic records.

## Anti-patterns

- Do not fabricate a resource header or bibliographic details.
- Do not quote ordinary prose as if it were a resource reference.
- Do not assume a page number is a physical PDF page when `offset:` differs.
