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
