# Build Expressions

Use `\type@value` to build a value at a stated type when the value already has
that type, reaches it through extension, or has an applicable `Enables: view:`.

```text
X := \set@{x_ : x_ is \real}
n := \rational@k
```

A top-level build on the right of a `Defines:` assignment supplies the required
explicit type, so `X := \set@{...}` is the typed alternative to `X is \set`
plus a separate body. A build is checked; it is not an arbitrary cast.

## Anti-patterns

- Do not use `@` to force an unrelated value into a type.
- Do not assume parsing proves the required view or extension exists.
- Do not add both a contradictory `is` type and build type.
- Do not use build syntax when an ordinary already-typed expression is clearer.
