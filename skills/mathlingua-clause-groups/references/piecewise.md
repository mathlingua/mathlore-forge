# `piecewise:`

Use `piecewise:` to define or assert ordered conditional branches.

```text
. piecewise:
  if: x < 0
  then: y := -x
  elseIf: x = 0
  then: y := 0
  else: y := x
```

The initial `if:` and `then:` are required. Any number of `elseIf:`/`then:`
pairs may follow, then one optional `else:`. Each conditional branch receives
its own assumed condition. `else:` is checked in the outer context.

## Anti-patterns

- Do not omit the `then:` paired with any `if:` or `elseIf:`.
- Do not put `else:` before all conditional pairs.
- Do not assume the checker proves branch exhaustiveness or disjointness.
- Do not use `Disambiguates:` for an ordinary piecewise value body.
