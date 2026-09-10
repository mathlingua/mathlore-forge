# `specifies:`

Use `specifies:` for facts or component values that belong to the construct.

```text
specifies:
. X is \set
. e "in" X
. op is \binary.operation:on{X}
```

In `Declares:`, these facts are carried by every instance. In concrete
`Defines:` and `Realizes:`, use `:=` to supply component values, unless a typed
callable component receives its value through `expresses:`. In `Refines:`, the
single refined-capable statement states the base or inherited refined fact.

Facts are processed in order. A target may be bound with `:=`; names on the
right must already be available. Assignments are followed during capability
inference.

## Anti-patterns

- Do not use predicate `is?` where `specifies:` is establishing a type fact.
- Do not leave a concrete component with only `is` and no value.
- Do not assign the same component twice.
- Do not use `specifies:` as a free-form list of theorem conclusions.
