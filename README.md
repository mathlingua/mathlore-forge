# Mathlore Forge

A durable, self-improving AI forge system designed to autonomously create and curate **Mathlore** (the comprehensive formal mathematics repository written in Mathlingua).

## Architecture

- **Harness**: [Google Antigravity SDK](https://github.com/google/antigravity)
- **Tooling**: Direct integration with the `mlg` compiler (`mlg check`, `mlg structure`, `mlg search`, `mlg format`)
- **Domain Skills**: Loaded from `skills/` containing structural, formulation, clause group, and workflow specifications
- **Isolated Roots**: Explicit `content_root` requirement ensuring tests and agents operate on targeted collections (e.g. temporary directories for golden tests) without searching the filesystem

## Mathlingua Authoring Agent

The Mathlingua agent is built on the Google Antigravity SDK. It is equipped with domain skills from `skills/` and tools to author Mathlingua content, execute `mlg` commands, and update `.mlg` files.

### Python API Usage

```python
from pathlib import Path
from mathlore_forge import create_mathlingua_agent, MathlinguaAgent

# Explicitly configure the Mathlingua content root (never searches filesystem)
content_root = Path("/path/to/mathlore")

# 1. Using high-level wrapper
async with MathlinguaAgent(content_root=content_root) as agent:
    response = await agent.chat(
        "write the definition of an abelian group in file 07_algebra/02_groups.mlg "
        "after item with ID e4d7371d-29bd-431f-ab09-e114fe89e5cf"
    )
    print(await response.text())

# 2. Or create standard Antigravity Agent
agent = create_mathlingua_agent(content_root=content_root)
```

### Subagent Usage

To equip another Antigravity agent with the Mathlingua author as a subagent:

```python
from google.antigravity import Agent, LocalAgentConfig
from mathlore_forge import create_mathlingua_subagent_config

math_subagent = create_mathlingua_subagent_config(
    content_root=content_root,
    name="mathlingua_author",
)

main_agent_config = LocalAgentConfig(
    subagents=[math_subagent],
    # ...
)
```

### CLI Usage

```bash
# Author content targeting an explicit content root
mathlore-forge author \
  --content-root /path/to/mathlore \
  --file 07_algebra/02_groups.mlg \
  --after-id e4d7371d-29bd-431f-ab09-e114fe89e5cf \
  --prompt "write the definition of an abelian group"

# Run mlg check on the content root
mathlore-forge check --content-root /path/to/mathlore
```

## Golden Testing Framework

`mathlore-forge` includes an isolated golden testing infrastructure (`mathlore_forge.goldens`) designed to evaluate Mathlingua authoring agents across addition, editing, and deletion tasks.

### Structure
- **Agent Code**: `src/mathlore_forge/agents/`
- **Compiler Client & Tools**: `src/mathlore_forge/mlg/`, `src/mathlore_forge/tools/`
- **Golden Test Infra**: `src/mathlore_forge/goldens/`
- **Golden Test Cases**: `golden_tests/`
- **Unit Tests**: `tests/`

### Features
1. **Isolated Sandboxing**: Each run creates a dedicated temporary sandbox under `runs/session-N/workspace/` with snapshot scaffold comparison.
2. **Unified Diffs**: Generates `changes.diff` showing exactly what the agent created, edited, or deleted.
3. **Trajectory Recording**: Logs agent reasoning, tool invocations, duration, and subagent calls to `trajectory.json` and human-readable `trajectory.md`.
4. **Compiler Verification**: Automatically executes `mlg check` in the workspace to verify 0 diagnostics.
5. **Sequential Session Management**: Allocates human-readable, monotonically increasing IDs (`session-1`, `session-2`, etc.).

### Golden CLI Usage

The golden test framework can be invoked via `mathlore-forge goldens <cmd>` or directly via the `mlg-golden <cmd>` shortcut:

```bash
# Run all golden tests against an agent
mlg-golden run --agent simulated
# or against the live Google Antigravity agent:
mlg-golden run --agent forge --model gemini-3.8-flash

# List all available golden test cases
mlg-golden tests

# Scaffold a new golden test case
mlg-golden new 04_define_vector_space --name "Define Vector Space"

# List prior test sessions and workspaces
mlg-golden runs

# Inspect a specific session run
mlg-golden show session-1

# View the unified diff patch of a session
mlg-golden diff session-1

# View execution trajectory (thoughts, tool calls, subagents)
mlg-golden trajectory session-1

# Clean up sessions
mlg-golden clean --all
mlg-golden clean --passed
```

