# Forms And Declarations

Forms describe reusable syntactic shapes; declarations optionally give those
shapes names or expansions.

```text
x
f(x_)
g ::= f(x_, y_)
G ::= g(x_) ::= y_
pt ::= (x_, y_)
set ::= {x_ : ...}
x_ |plus| y_
```

Use `::=` for declaration/shape expansion, not value assignment. Function forms
accept one magnetic placeholder or one or more ordinary placeholders. Tuple
forms require at least two elements. Declarations can combine `::=` with `:=`
inside binding contexts to create a local syntactic substitution.

```text
where:
. A ::= B := B
```

See [names and placeholders](names-and-placeholders.md) and
[statements](statements-and-specifications.md).

## Anti-patterns

- Do not use a one-element tuple form; it is unsupported.
- Do not use `:=` to describe an interface shape.
- Do not introduce the same bound name twice in one inherited scope.
- Do not confuse the alias name on the left of `::=` with a separately typed
  value unless the surrounding statement establishes that type.
