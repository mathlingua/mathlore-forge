# Local `Writing:`

Use an item-local `Writing:` section after `Aliases:` and before `References:`
to override plain-name rendering only within that item.

```text
Writing:
. "pi :~> \varpi"
```

The value is a quoted raw rendering alias. For collection-wide behavior, use a
top-level [`Writing:` group](../../mathlingua-structural-language/references/writing.md).

## Anti-patterns

- Do not use a local alias when every item should render the name that way.
- Do not expect this section to rename symbols semantically.
- Do not place it before `Aliases:` or after `References:`.
