# How Do I Add A Reusable Proposition?

Use `States:` when callers should be able to invoke a named proposition.

1. Read [`States:`](../../mathlingua-structural-language/references/states.md),
   [command headers](../../mathlingua-formulation-language/references/command-headers.md),
   and the needed [clause group](../../mathlingua-clause-groups/SKILL.md).
2. Bind and type every heading parameter in `when:`.
3. Put the proposition in required `that:` and add readable documentation.

```text
[P \.implies./ Q]
States:
when: P, Q is \\statement
that:
. if: P
  then: Q
Documented:
. called: "$P?$ implies $Q?$"
```

## Do not

- Do not put an argument after `States:`.
- Do not use `States:` for a theorem with local hypotheses and a one-off name.
- Do not use unbound symbols in `that:`.
- Do not assume a command's rendered notation reveals its source signature.
