---
name: mathlore-diagnose-content
description: Diagnose and fix MathLingua syntax, semantic, scope, requirement, formatting, ID, or rendering problems in the Mathlore collection. Use when mlg check fails, content does not render as intended, or the user asks to audit existing .mlg content. Do not use to change the MathLingua compiler unless separately requested.
---

# Diagnose Mathlore Content

Find the first real content error, make the smallest mathematically faithful
fix, and leave the complete collection checking cleanly.

Read [references/diagnostic-playbook.md](references/diagnostic-playbook.md)
before changing files.

## Workflow

1. Confirm the Mathlore root (`mlg.json`, `content/`) and inspect repository
   status so unrelated changes are preserved.
2. Reproduce the issue with the current checker and retain the exact diagnostic,
   file, line, and any source changes caused by formatting or ID insertion.
3. Read the complete failing group, the referenced command definitions, and the
   surrounding assumptions. Diagnose from the earliest error; later errors may
   be cascades.
4. Fix content, not symptoms. Do not replace a strong type with `\\anything`,
   delete requirements, turn a theorem into opaque prose, or alter the intended
   claim solely to silence the checker.
5. Rerun a targeted check while iterating, then the full collection check with
   no path. Inspect the final diff.

## Boundaries

- Do not hand-edit generated `docs/`.
- Do not run `build.sh` or `mlg export --force` for diagnosis.
- Do not edit `../mathlingua` unless evidence shows a compiler defect and the
  user authorizes a compiler change.
- If a cleanly parsed, well-scoped construction appears to expose a compiler
  bug, minimize it and report the evidence; do not silently work around it by
  changing the mathematics.
