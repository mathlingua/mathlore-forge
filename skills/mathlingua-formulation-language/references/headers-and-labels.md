# Headers And Labels

Square-bracket headings have different parsers according to the following group:

```text
[\function:on{A}:to{B}]  -- command header
[#real.analysis]          -- topic header
[@ada.lovelace]           -- author header
[$example.book]           -- resource header
[step-one]                -- local label header
```

Command headings define signatures and bind parameters. Topic, author, and
resource headings use their sigils plus dotted paths. A local label may head a
clause or justification entry.

Expression/formulation labels are different and follow grouped formulations:

```text
(. x = y .)[:symmetry:]
```

Use the label spelling consistently between a labeled formulation and its
`Justification:` entry.

## Anti-patterns

- Do not use one heading kind where another is required.
- Do not assume any heading determines the structural group kind.
- Do not confuse `[label]` group headings with `[:label:]` formulation labels.
- Do not create duplicate command signatures or resource identities.
