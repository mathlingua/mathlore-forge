# Mathlore Forge

A durable, self-improving AI forge system designed to autonomously create and curate **Mathlore** (the comprehensive formal mathematics repository written in Mathlingua).

## Architecture

- **Harness**: [Google Antigravity SDK](https://github.com/google/antigravity)
- **Durable Execution**: [DBOS Transact](https://dbos.dev/)
- **Observability**: OpenTelemetry spans, live trace watching, and past execution inspection
- **Self-Improvement**: Flywheel learning from user feedback and automated golden test case regression testing
- **Tooling**: Direct integration with the `mlg` compiler (`mlg check`, `mlg structure`, `mlg search`)

## Getting Started

```bash
# Sync dependencies
uv sync

# Run the forge in interactive mode
uv run mathlore-forge run --interactive

# Run the forge in autonomous mode with steering
uv run mathlore-forge run --auto --max-iterations 3 --steer "Add theorems on partial orders"

# Inspect past execution traces
uv run mathlore-forge traces list
uv run mathlore-forge traces show <trace_id>

# Run regression evaluation on golden cases
uv run mathlore-forge eval
```
