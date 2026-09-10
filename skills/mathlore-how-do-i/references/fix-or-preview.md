# How Do I Fix Or Preview Content?

For failures, load [the diagnostic skill](../../mathlore-diagnose-content/SKILL.md).

1. Reproduce the exact first meaningful diagnostic from the collection root.
2. Read the complete failing group and each referenced command definition.
3. Follow the error into the narrow structural, formulation, clause, or support
   reference linked from the top-level authoring skill.
4. Make the smallest mathematically faithful fix.
5. Iterate with a filtered path if useful, then run an unfiltered full check.
6. Inspect formatter and generated-ID changes.

For visual verification, use `mlg view` and inspect the affected cards. Preview
is distinct from publishing.

## Do not

- Do not patch later cascade errors before the first real cause.
- Do not replace meaningful types with `\\anything`, remove requirements, or
  turn structured content into opaque prose just to pass.
- Do not run `build.sh` or `mlg export --force` merely to preview.
- Do not edit the compiler unless the user authorizes a compiler change.
