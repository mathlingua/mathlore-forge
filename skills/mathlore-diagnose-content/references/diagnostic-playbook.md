# Mathlore Diagnostic Playbook

## Reproduce safely

From the collection root, use the first available checker:

1. `mlg check`
2. `../mathlingua/target/debug/mlg check`
3. `cargo run --manifest-path ../mathlingua/Cargo.toml -- check`

An explicit source path filters displayed diagnostics while the checker still
loads the whole collection. Finish with an unfiltered check.

Because checking can format `.mlg` files and insert missing `Id:` sections,
inspect the working-tree diff immediately after reproduction. Do not confuse
those expected writes with the attempted fix.

## Diagnose by layer

### Collection and configuration

- Missing/extra `toc` entry: every direct `.mlg` file or directory must occur
  exactly once in that directory's `toc`; `_preface_.mlg` is excluded.
- Invalid config: preserve all required `mlg.json` fields and their types.
- Duplicate/malformed `Id:`: never copy IDs; remove the bad ID from a genuinely
  new item and let the checker generate one.

### Structural syntax

Symptoms include unexpected group/section errors or content parsed as a nested
group.

- Group kind comes from the first section label, not the bracket heading.
- Labels are case-sensitive and section order is strict.
- A dot argument adds two spaces of logical indentation.
- Structural labels use exact spellings such as `Documented:`, `Requires:`, and
  `Enables:`; clause labels such as `forAll:`, `suchThat:`, and `elseIf:` retain
  their casing.
- Compare the group with a checked neighboring example before moving sections.

### Formulation syntax

- Match delimiters and command argument groups exactly.
- Distinguish `::=` (structure), `:=` (value), `is` (specification), and `is?`
  (predicate).
- Builtin types use two leading backslashes in source.
- Direct concrete components use `..` in source even though the viewer renders
  one dot.
- A rendered template is not evidence of the underlying command signature;
  inspect its heading.

### Signatures and references

- Search for the exact command definition and compare argument shape.
- Optional command tails must keep their declared order.
- Duplicate signatures may arise across files and across different top-level
  definition kinds.
- For an undefined command, prefer the established command path if one already
  expresses the concept; otherwise add a definition only when the task requires
  a new concept.

### Scope and duplicate symbols

- Every right-hand expression, command argument, and spec target must use names
  introduced earlier in the relevant scope.
- Header parameters and target symbols must not be redeclared in `using:` or a
  nested binding.
- Nested quantifiers and `let:` groups cannot shadow an enclosing defined
  symbol. Rename the inner binder and all uses consistently.
- Repeated function-form placeholders are allowed; repeated callable names are
  not.
- In conclusions, use `is?` or predicate spec forms instead of introducing a
  fresh `is` fact.

### Requirements and facts

- Read the referenced command's `when:` section and prove each requirement from
  facts already in scope.
- Put constraints on header parameters in the current definition's `when:`;
  `when:` cannot constrain unrelated names.
- Check whether a needed fact comes from a type's `extends:`, `specifies:`,
  `Requires:`, `Enables:`, or a view. Do not add duplicate specifications.
- A spec operator must be provided by the target type.

### Defines/Realizes target errors

- A concrete `Defines` needs an explicit type.
- Every concrete target part needs one value through `:=` or `expresses:`.
- `abstractly:` intentionally leaves parts open; `Realizes:` must supply all of
  them and name the abstract definition with `:=`.
- Duplicate component assignments and assignment-backed `specifies:` facts are
  followed by the checker; inspect aliases/substitutions before adding another
  fact.

### Documentation and rendering

- `Declares`, `Defines`, `Realizes`, and `States` need `called:` or `written:`.
- `Refines` needs `adjective:` and rejects `called:`.
- Template placeholders must correspond to heading/form parameters. For `n_`,
  both `n_?` and `n?` match.
- For incorrect visual output, inspect the source command, its `Documented:`
  template, and the concrete arguments separately.

## Decide content bug versus compiler bug

Assume a content bug until all of these are true:

1. The source matches documented syntax and a nearby accepted pattern.
2. Every symbol and requirement can be enumerated from the source.
3. The same issue survives in a minimal isolated collection.
4. Current compiler tests or docs imply the construction should work.

If those conditions hold, report the minimal source, actual diagnostic/output,
expected behavior, and compiler version. Seek authorization before changing the
compiler repository.

## Finish

- Run the full checker with no path.
- Confirm no unrelated source or generated site files changed.
- Re-read the corrected mathematical statement and rendered template.
- Summarize the root cause, not only the line edited.
