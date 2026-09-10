# Operators And Member Access

MathLingua distinguishes several operator and member forms:

```text
x |op| y               -- named infix operator
neg| x                 -- named prefix operator
x |prime               -- named postfix operator
x \.set.union./ y      -- infix command
M.X                     -- component of a bound value
M.`*`(x, y)             -- bound operator member call
\naturals..N            -- direct component of a Defines/Realizes command
\naturals..succ(n)      -- direct callable component
\reals..`*`             -- direct operator component
```

Use one dot for an ordinary bound value and two dots for a direct component of a
top-level `Defines:` or `Realizes:` command. Direct components are valid as
ordinary expressions and as specification subjects or targets; the renderer
shows one dot even though source keeps `..`.

## Anti-patterns

- Do not copy the rendered single-dot spelling for direct command components.
- Do not omit backticks around an operator used as a member name/value.
- Do not treat named operators and infix commands as the same precedence level.
- Do not use direct access on a `Declares:` type; it applies to defined values.
