# `Specify:`

Use one collection-level `Specify:` group to configure fallback types for
numeric literals and variadic indexes.

```text
Specify:
. decimal:
  is: \real
. zeroOrPositiveInt:
  is: \whole
. positiveInt:
  is: \natural
. int:
  is: \integer
```

Each `is:` value must be a nominal or built-in type expression. Local scope and
derived facts take precedence; these types are fallbacks. Zero-based variadic
indexes use `zeroOrPositiveInt`; one-based indexes use `positiveInt`.

## Anti-patterns

- Do not add multiple `Specify:` groups.
- Do not treat these entries as declarations of the number commands themselves.
- Do not use an expression that is not a valid type.
