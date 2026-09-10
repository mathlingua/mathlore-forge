# Code Examples In Prose

Quoted `Text:` and documentation values may contain Markdown fenced code.

- Use an `mlg` fence when the example is complete source that should parse and
  check as a document.
- Use `mlg-fragment` when the excerpt is intentionally incomplete and should
  not be parsed as a complete document.

```text
Text: "For example:

       ```mlg-fragment
       when: A is \\set
       ```
       "
```

Multiline quoted text continues until the closing quote used by the surrounding
source style. Run `mlg check` and inspect formatter reflow and fence indentation.
An `mlg` fence is syntax-checked as a standalone document, but is not
semantically type-checked against the collection.

## Anti-patterns

- Do not label broken or incomplete source `mlg`; the checker will parse it.
- Do not use `mlg-fragment` to conceal an example that ought to be valid.
- Do not assume formatter reflow preserves a poorly indented fence.
