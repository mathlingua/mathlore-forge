# Organization Validation

From the collection root, run the first available full check:

1. `mlg check`
2. `../mathlingua/target/debug/mlg check`
3. `cargo run --manifest-path ../mathlingua/Cargo.toml -- check`

The checker reports missing, duplicate, and nonexistent `toc` entries. It may
also format source and insert IDs, so inspect the complete diff afterward.

Verify separately that navigation order, display titles, hidden state, page
titles, and directory overviews match the requested reader experience.

## Anti-patterns

- Do not stop after a path-filtered diagnostic run; finish with the full check.
- Do not overlook unrelated formatter or ID changes.
- Do not run `build.sh` or a forced export for routine validation.
