# Mathlore Forge

A durable, self-improving AI forge system designed to autonomously create and curate **Mathlore** (the comprehensive formal mathematics repository written in Mathlingua).

📖 **Documentation Quick Links**:
- 👉 [**User Guide & Operator Manual (USER_GUIDE.md)**](USER_GUIDE.md): Human-oriented, step-by-step guide explaining the issue-to-merge lifecycle, reviewing PRs, slash commands, and local/production workflows.
- 👉 [**Terraform Deployment & Operations Manual (DEPLOYMENT.md)**](DEPLOYMENT.md): Complete guide for deploying to GCP Cloud Run, rolling updates, tearing down instances, and GitHub webhook setup.

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

## Autonomous Workflow & Web Dashboard

Mathlore Forge includes a real-time web dashboard and automated GitHub workflow engine:
- **Webhook Receiver**: Listens for issues, pull request reviews, and comments from Dominic Kramer.
- **Authoring Worker**: Automatically checks out `mathlore`, authors content, checks via `mlg`, and opens PRs.
- **Review Loop**: Automatically addresses review feedback from Dominic and updates PRs.
- **Self-Improvement Flywheel**: Synthesizes new rules in `skills/mathlore-learned-guidelines/SKILL.md` and golden tests before merging.
- **Google OAuth Dashboard**: Real-time visibility into running agents, complete trajectories, and controls, restricted to `DominicKramer@gmail.com`.

### 1. Running Locally (Try Before Rollout)
```bash
# Start the Web Dashboard and Webhook server on http://localhost:8080
uv run mathlore-forge serve --port 8080 --reload

# Run worker task locally against an issue or PR
uv run mathlore-forge worker --repo mathlingua/mathlore --issue 42
uv run mathlore-forge worker --repo mathlingua/mathlore --pr 43
```

### 2. Creating a New Deployment on GCP (Terraform)
```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"

# 1. Build initial container image
gcloud builds submit --tag "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/mathlore-forge/app:latest" -f infra/Dockerfile .

# 2. Provision infrastructure with Terraform
cd infra/terraform
terraform init
terraform apply -var="project_id=$GCP_PROJECT_ID" -var="region=$GCP_REGION"
```

### 3. Updating an Existing Deployment (Rollout Changes)
```bash
# 1. Build and tag image with git commit SHA
TAG=$(git rev-parse --short HEAD)
gcloud builds submit --tag "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/mathlore-forge/app:${TAG}" -f infra/Dockerfile .

# 2. Declaratively roll out the revision
cd infra/terraform
terraform apply -var="project_id=$GCP_PROJECT_ID" -var="region=$GCP_REGION" -var="image_tag=$TAG"
```

### 4. Tearing Down & Stopping All Instances
```bash
cd infra/terraform
terraform destroy -var="project_id=$GCP_PROJECT_ID" -var="region=$GCP_REGION"
```

For full step-by-step instructions (with explanations of what each step does and why it is needed), GitHub webhook setup, secret configurations, and instant rollback procedures, see the comprehensive guide:
👉 **[DEPLOYMENT.md](DEPLOYMENT.md)**

