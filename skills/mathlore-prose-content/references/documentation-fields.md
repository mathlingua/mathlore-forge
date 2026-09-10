# Documentation Fields

Use `Documented:` fields to make a structured item readable and discoverable.

- `called:` gives a prose name and may include `$...$` substitutions.
- `written:` gives a math-mode rendering template.
- `adjective:` names a `Refines:` property and is required there.
- `description:` explains meaning or purpose.
- `writing:`/`as:` supplies mapping-specific notation.
- `overview:`, `related:`, `discoverer:`, and `notes:` are specialized; follow a
  nearby checked example.

```text
Documented:
. called: "function from $A?$ to $B?$"
. written: "A? \\rightarrow B?"
. description: "A mapping from each element of $A?$ to an element of $B?$."
```

Definition groups require at least a usable name or notation. `Refines:` uses
`adjective:` and rejects `called:`. Text placeholders accept only `called:`,
`written:`, `description:`, and `notes:`.

## Anti-patterns

- Do not use a field unsupported by the parent group.
- Do not write a generic description that adds no reader value.
- Do not describe parameters under different names than the heading uses.
- Do not put a formula's semantic definition in `written:`; it controls display.
