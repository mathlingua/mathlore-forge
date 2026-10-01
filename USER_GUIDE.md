# Mathlore Forge: User Guide & Operator Manual

Welcome to **Mathlore Forge**! This guide is written for humans to clearly explain how Mathlore Forge works, how to use it day-to-day, how the authoring and review lifecycle operates, and how to control everything directly through GitHub and the Web Dashboard.

---

## Table of Contents

1. [What is Mathlore Forge?](#1-what-is-mathlore-forge)
2. [The Complete Lifecycle: From Issue to Landed Content](#2-the-complete-lifecycle-from-issue-to-landed-content)
   - [Step 1: Filing a Request (GitHub Issue)](#step-1-filing-a-request-github-issue)
   - [Step 2: Autonomous Authoring & PR Creation](#step-2-autonomous-authoring--pr-creation)
   - [Step 3: Inspecting Results on the Web Dashboard](#step-3-inspecting-results-on-the-web-dashboard)
   - [Step 4: Requesting Changes (The Review Loop)](#step-4-requesting-changes-the-review-loop)
   - [Step 5: Approving & Landing the PR](#step-5-approving--landing-the-pr)
   - [Step 6: The Self-Improvement Flywheel](#step-6-the-self-improvement-flywheel)
3. [Higher-Order Requests & The Curator Agent (Interactive Planning)](#3-higher-order-requests--the-curator-agent-interactive-planning)
   - [Direct Authoring vs. Strategic Planning](#direct-authoring-vs-strategic-planning)
   - [How the Planning Workflow Operates](#how-the-planning-workflow-operates)
   - [Interactive Proposal Refinement Loop](#interactive-proposal-refinement-loop)
   - [Executing an Approved Plan](#executing-an-approved-plan)
4. [Slash Commands Reference](#4-slash-commands-reference)
5. [Running Locally vs. Production on GCP](#5-running-locally-vs-production-on-gcp)
   - [Local Development Workflow](#local-development-workflow)
   - [Production Cloud Workflow](#production-cloud-workflow)
6. [Troubleshooting & Frequently Asked Questions](#6-troubleshooting--frequently-asked-questions)


---

## 1. What is Mathlore Forge?

**Mathlore** is the community knowledgebase of formal mathematics written in the **Mathlingua** language. 

**Mathlore Forge** is an autonomous, self-improving AI forge system powered by the **Google Antigravity SDK** and **Gemini 3.8**. It acts as an active, round-the-clock mathematical collaborator that:
- Reads your requests in GitHub issues.
- Navigates the Mathlore repository structure.
- Formulates mathematically rigorous definitions, theorems, and proofs.
- Validates every item with the `mlg` compiler (`mlg check`) to ensure valid syntax and zero errors.
- Formats code according to official print standards (`mlg format`).
- Opens clean Pull Requests on GitHub.
- Listens to your code review feedback, modifies its code, and replies to comments.
- **Learns from every review you give it**: when a PR lands, it analyzes your feedback, saves new authoring guidelines into its skills library, and generates automated golden tests so it never makes the same mistake again.

---

## 2. The Complete Lifecycle: From Issue to Landed Content

```
   Dominic Kramer
        │
        │ 1. Creates Issue with [forge] label
        ▼
   GitHub Issue ────────► Mathlore Forge Webhook Receiver
                                │
                                │ 2. Launches Authoring Flow
                                ▼
                       Antigravity Authoring Agent
                       • Explores files & references
                       • Formulates Mathlingua
                       • Runs `mlg check` & `mlg format`
                       • Commits to new branch
                                │
                                │ 3. Opens Pull Request
                                ▼
                       GitHub Pull Request #N
                                │
            ┌───────────────────┴───────────────────┐
            │                                       │
            ▼ (Feedback Needed)                     ▼ (Accepted!)
  Dominic leaves review comments         Dominic comments `/forge accept`
            │                                       │
            ▼                                       ▼
  Comments Trigger Review Flow             Self-Improvement Flywheel
  • Agent reads comments                  • Extracts lessons learned
  • Fixes `.mlg` files in branch          • Updates `SKILL.md` guidelines
  • Runs `mlg check`                      • Creates golden test
  • Pushes new commit                     • Opens PR in `mathlore-forge`
  • Replies to comment threads            • Squash-merges Mathlore PR #N
            │                             • Closes Issue
            └───────────────────────────────────────┘
```

---

### Step 1: Filing a Request (GitHub Issue)

To request new mathematical content:
1. Go to **[mathlingua/mathlore Issues](https://github.com/mathlingua/mathlore/issues)**.
2. Click **New Issue**.
3. In the title, include the prefix **`[Forge]`** (or apply the label **`forge`**):
   ```
   [Forge] Add monotonicity of set intersection
   ```
4. In the issue description, describe what mathematical concept, theorem, definition, or axiom should be added and (optionally) the target file:
   ```markdown
   Please add a theorem to `01_set_theory/04_operations.mlg` stating that:
   If A, B, and C are sets and A is a subset of B, then (A ∩ C) is a subset of (B ∩ C).
   
   Include a complete proof and standard mathematical citations.
   ```
5. Click **Submit new issue**.

> **Security Guard**: Only issues opened by authorized authors (`DominicKramer`) trigger agent authoring. Issues opened by unauthorized users are ignored.

---

### Step 2: Autonomous Authoring & PR Creation

Once the issue is detected, Mathlore Forge automatically executes the authoring workflow:

1. **Workspace Setup**: Sets up an isolated Git workspace targeting the Mathlore collection.
2. **Skill Loading**: Injects domain skills (Mathlingua syntax rules, clause group specifications, mathematical documentation standards).
3. **Exploration & Insertion**:
   - The agent reads existing related files (e.g. `01_set_theory/04_operations.mlg`).
   - Finds appropriate insertion points after existing definitions.
   - Formulates the item in Mathlingua notation.
4. **Verification & Formatting**:
   - Runs `mlg check` against the collection. If any compiler diagnostic occurs, the agent self-corrects until 0 errors remain and a UUID is generated.
   - Runs `mlg format` to ensure uniform indentation and print margins.
5. **Pull Request Opened**:
   - Creates a dedicated branch: `forge/issue-<number>-<slug>`.
   - Commits the validated changes.
   - Pushes the branch and opens a Pull Request on GitHub titled `[Forge] <Issue Title> (closes #<number>)`.
   - The PR description contains the full mathematical summary, formulated theorem, proof, and references.

---

### Step 3: Inspecting Results on the Web Dashboard

You can monitor and inspect agent activities at any time on the Web Dashboard:
- **Local URL**: [http://localhost:8080](http://localhost:8080)
- **Production URL**: Your deployed Cloud Run HTTPS URL

#### Main Dashboard (`/`):
- **Metrics**: Active agent tasks, runs awaiting review, completed tasks, and total tokens used.
- **Runs Table**: Real-time listing of all runs, target repositories, branch names, PR links, and token consumption.
- **Quick Output Preview**: Every row has an **Output** button. Clicking it expands the authored Mathlingua theorem and proof directly in the table.

#### Trajectory Inspector (`/runs/<run_id>`):
- **Authored Mathlingua Result**: The formulated definition/theorem, proof, and citations prominently highlighted.
- **Execution Overview**: Links directly to the GitHub PR and branch.
- **Tool Calls Tab**: Step-by-step breakdown of every single tool action the agent took (e.g. file reads, `mlg check` compiler passes, `mlg format`).
- **Unified Diff Tab**: Color-coded unified Git patch of all modifications.
- **Audit Log**: Complete detailed Markdown trace of the entire session.

---

### Step 4: Requesting Changes (The Review Loop)

If the generated Mathlingua content needs revisions, corrections, or additional items, you can request changes directly inside GitHub.

#### How to Leave Feedback:
1. Open the Pull Request on GitHub.
2. Go to the **Files changed** tab.
3. Hover over the line of code you want modified and click the blue **`+`** icon.
4. Write your feedback:
   - *"Please add an alias called 'Intersection Monotonicity'"*
   - *"Change the notation in line 180 to use \setminus instead of \minus"*
   - *"Add a brief explanatory comment above the proof"*
5. Click **Start a review** (or **Add single comment**). You can leave comments on as many lines as needed.
6. When finished:
   - Click **Review changes** at the top right, select **Request changes**, and submit.
   - OR, post a comment in the PR conversation:
     ```
     /forge address
     ```

#### What Happens Next:
1. Mathlore Forge detects your review comments.
2. The agent checks out the PR branch, reads all unresolved comments and their exact line context.
3. Modifies the code to implement your requested changes.
4. Re-validates with `mlg check` and `mlg format`.
5. Commits and pushes the updates directly to the existing PR branch.
6. Automatically replies to each of your review comments on GitHub explaining what was done!

---

### Step 5: Accepting & Merging the PR

When the PR is ready to be merged:

#### Option A: Comment `/forge accept` (Recommended)
On the PR conversation tab, leave a comment:
```
/forge accept
```

> **Why this is recommended**: Commenting `/forge accept` triggers automated pre-merge quality validation (`mlg check`), runs self-healing if needed, waits for all CI checks to pass, extracts flywheel learnings, and squash-merges into `main`. It also cleanly bypasses GitHub's restriction preventing PR authors from clicking native "Approve".

#### Option B: Native GitHub Approval
If your repository branch protection settings allow approving your own PR:
1. Go to **Files changed**.
2. Click **Review changes**.
3. Select **Approve** and click **Submit review**.

---

### Step 6: The Self-Improvement Flywheel

Once approved, Mathlore Forge does not just merge the code—it **learns from the interaction**:

1. **Feedback Reflection**:
   If you left any review comments during the PR's lifecycle, the **Reflection Agent** analyzes:
   - What the agent initially did wrong or suboptimal.
   - What principle or preference you expressed.
   - How to formalize this into a permanent rule.
2. **Guideline Update**:
   Synthesizes the new rule into [`skills/mathlore-learned-guidelines/SKILL.md`](skills/mathlore-learned-guidelines/SKILL.md).
3. **Golden Test Generation**:
   Generates a new automated test case under `golden_tests/` capturing your scenario to permanently prevent regression.
4. **Self-Improvement PR**:
   Opens a Pull Request in `mathlingua/mathlore-forge` containing the updated guidelines and golden test.
5. **Squash-Merge Mathlore PR**:
   Automatically squash-merges the approved PR into `main` on `mathlingua/mathlore`.
6. **Closes Issue**:
   Closes the original issue with a celebratory summary and links.

---

## 3. Higher-Order Requests & The Curator Agent (Interactive Planning)

Not all mathematical requests are as concrete as *"add theorem X to file Y"*. Often, you want to guide Mathlore at a higher strategic, architectural, or pedagogical level:
- *"I want to add more number theory content to Mathlore."*
- *"What is the next logical chapter that should be written after Group Theory?"*
- *"We need a pedagogical overhaul of chapter 02 to make the exposition more intuitive."*
- *"Restructure the topological spaces definitions to introduce Hausdorff spaces and compact sets."*
- *"Update the tone and prose across the set theory chapters to be more accessible."*

For these requests, Mathlore Forge activates its **Curator / Architect Agent**. Rather than jumping straight into writing files or opening code PRs without alignment, the Curator Agent investigates the repository, formulates an **Architectural Action Plan (Proposal)**, posts it on GitHub, and notifies you at `DominicKramer@gmail.com`. You can then comment back and forth to refine the plan until you are satisfied. Only once you approve does the system spawn authoring subagents to write the code.

---

### Direct Authoring vs. Strategic Planning

The system automatically distinguishes between two types of requests using an **Intent Classifier**:

| Request Mode | Description | Example Issue Title | What Forge Does |
| :--- | :--- | :--- | :--- |
| **Direct Authoring** | Concrete additions to specific existing files. | `[Forge] Add subset monotonicity theorem to 01_set_theory/04_operations.mlg` | Directly authors `.mlg` code, runs `mlg check`, and opens a code PR. |
| **Higher-Order Planning** | Abstract goals, content proposals, roadmap, structural overhauls, or curriculum design. | `[Forge] Add more number theory content` or `[Forge] What should the next logical chapter be?` | Launches the **Curator Agent**, researches repo coverage and pedagogical prerequisites, drafts a detailed Proposal on the issue, and waits for your approval. |

> [!TIP]
> You can explicitly force Forge to plan any issue by including the label `plan` or prefixing the title with `[Plan]`, e.g. `[Forge][Plan] Introduce Measure Theory`.

---

### How the Planning Workflow Operates

```
Dominic Kramer creates Abstract Issue
("I want to add more number theory content")
                    │
                    ▼
           Intent Classifier
      (HIGHER_ORDER_PLANNING detected)
                    │
                    ▼
          Curator / Architect Agent
  • Surveys Mathlore content & directory structure
  • Inspects existing `toc` tables of contents
  • Evaluates prerequisite coverage & mathematical dependencies
  • Synthesizes pedagogical goals & chapter outline
                    │
                    ▼
     Posts Architectural Action Plan to Issue
                    │
                    ▼
    Notifies Dominic (DominicKramer@gmail.com)
  • GitHub @DominicKramer mention
  • Direct Email alert (via SMTP if configured)
                    │
                    ▼
         Awaiting Your Review & Feedback
```

---

### Interactive Proposal Refinement Loop

When the Curator Agent posts its proposal, you will receive an alert. You can review the proposed chapters, sections, items, and verification strategy directly on the GitHub issue.

If you want changes to the plan:
1. Leave a comment directly on the issue:
   - *"Let's focus on prime factorization and modular arithmetic first, before touching Diophantine equations."*
   - *"Make sure the definitions include aliases for standard notation."*
   - *"Place this under a new top-level chapter 08_number_theory."*
2. The Curator Agent automatically reads your feedback, incorporates your instructions, and posts **Revision 2** of the proposal to the issue.
3. You can continue this interactive refinement dialog as many times as you like until the plan is perfect.

---

### Executing an Approved Plan

Once you are satisfied with the proposal:

#### In GitHub:
Leave a comment on the issue:
```
/forge accept
```

#### On the Web Dashboard:
Navigate to [http://localhost:8080](http://localhost:8080). You will see the issue marked with the purple **Plan Proposed** badge. Click the **Execute** button next to the run.

#### Using the CLI:
```bash
# Execute the approved plan for an issue
uv run mathlore-forge plan --repo mathlingua/mathlore --issue 42 --execute

# Or via worker
uv run mathlore-forge worker --repo mathlingua/mathlore --execute-plan 42
```

#### What Happens When Executed:
1. Forge acknowledges your approval with a comment on the GitHub issue.
2. The Curator Agent spawns the **Mathlingua Authoring Subagent**.
3. The authoring agent:
   - Creates any necessary directories (e.g. `08_number_theory/`).
   - Generates chapter prefaces (`_preface_.mlg`) and updates `toc` tables of contents.
   - Formulates the mathematical items (Definitions, Theorems, Axioms, Proofs).
   - Validates everything with `mlg check` to ensure 0 errors and unique UUIDs.
   - Formats the files with `mlg format`.
4. Opens the Pull Request on GitHub and links it back to your issue.

---

## 4. Focused Commands Reference
 
Mathlore Forge uses a minimal, focused set of commands so that the workflow is completely consistent:

| Command | Where to Use | Action |
| :--- | :--- | :--- |
| **`/forge accept`** | **Issue Conversation** | Accepts the latest revision of the curation proposal, authors the content, validates via `mlg check`, and opens a PR. |
| **`/forge accept`** | **PR Conversation** | Accepts the pull request, runs quality gates (`mlg check`), waits for CI checks, captures flywheel learnings, and merges into `main`. |
| **`/forge address`** | **PR Conversation** | Instructs the agent to read all unresolved review comments on the PR, modify code, re-test with `mlg check`, and push a new commit. |
| *(plain comment)* | **Issue Conversation** | Any comment on an issue with a proposed plan is treated as feedback and generates a refined proposal revision. |

> **Graceful Aliases**: Legacy aliases such as `/forge execute` on issues or `/forge approve` on PRs continue to be supported for backwards compatibility, but `/forge accept` is the single canonical command for accepting at any stage.

---

## 5. Running Locally vs. Production on GCP

### Local Development Workflow

When working locally on your development machine:

```bash
# 1. Start the server (auto-reloads on code edits)
# DEV_ALLOW_LOCAL_ADMIN=true logs you in as Dominic Kramer automatically without OAuth setup
DEV_ALLOW_LOCAL_ADMIN=true uv run mathlore-forge serve --port 8080 --host 127.0.0.1 --reload

# Open http://localhost:8080 in your browser.
```

#### Working with Plans via CLI:

```bash
# 1. Formulate a proposal for an abstract GitHub issue:
uv run mathlore-forge plan --repo mathlingua/mathlore --issue 42

# 2. Formulate an ad-hoc proposal without an existing issue:
uv run mathlore-forge plan --title "Number Theory Foundations" --prompt "Add divisibility, primes, and modular arithmetic"

# 3. Refine an existing proposal with feedback:
uv run mathlore-forge plan --repo mathlingua/mathlore --issue 42 --refine "Focus on Euclidean algorithm and primes first"

# 4. Execute the approved plan and submit the PR:
uv run mathlore-forge plan --repo mathlingua/mathlore --issue 42 --execute
```

#### Triggering Background Workers:

```bash
# Test authoring for a direct issue
uv run mathlore-forge worker --repo mathlingua/mathlore --issue 1

# Test planning for an abstract issue
uv run mathlore-forge worker --repo mathlingua/mathlore --plan-issue 42

# Test executing an approved plan
uv run mathlore-forge worker --repo mathlingua/mathlore --execute-plan 42

# Test addressing review comments on a PR
uv run mathlore-forge worker --repo mathlingua/mathlore --pr 1

# Test the pre-merge flywheel and merge on a PR
uv run mathlore-forge worker --repo mathlingua/mathlore --flywheel-pr 1
```

#### Simulating Webhooks with `curl`:

```bash
# Simulate an abstract planning issue opened:
curl -X POST http://127.0.0.1:8080/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -d '{
    "action": "opened",
    "issue": {
      "number": 42,
      "title": "[Forge] Add more number theory content",
      "body": "We need foundational number theory: prime factorization and modular arithmetic.",
      "user": {"login": "DominicKramer"},
      "labels": [{"name": "forge"}]
    },
    "sender": {"login": "DominicKramer"},
    "repository": {"full_name": "mathlingua/mathlore"}
  }'

# Simulate Dominic approving the plan via comment:
curl -X POST http://127.0.0.1:8080/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issue_comment" \
  -d '{
    "action": "created",
    "issue": {
      "number": 42
    },
    "comment": {
      "body": "/forge execute",
      "user": {"login": "DominicKramer"}
    },
    "repository": {"full_name": "mathlingua/mathlore"}
  }'
```

---

### Production Cloud Workflow

In production, Mathlore Forge runs on **Google Cloud Platform (Cloud Run)** provisioned via **Terraform**:
- **Automatic Webhooks**: GitHub delivers webhooks directly to your public Cloud Run HTTPS URL.
- **No Manual Intervention**: Opening abstract issues, leaving feedback comments, commenting `/forge execute`, and commenting `/forge approve` on GitHub works completely automatically.
- **Secure Authentication**: The web dashboard is secured by Google OAuth 2.0 and strictly limited to `DominicKramer@gmail.com`.

#### Interactive Guided Deployment:
You can deploy everything automatically using the interactive script:
```bash
./deploy.sh
```
The script steps through all requirements, previews every command before execution, and asks for your confirmation at each step.

For full step-by-step instructions on deploying to GCP, see [**`DEPLOYMENT.md`**](DEPLOYMENT.md).

---

## 6. Troubleshooting & Frequently Asked Questions

### 1. GitHub says my token is "Never used" or returns `401 Unauthorized`
- **Cause**: By default, environment variables already exported in your terminal session can shadow variables in `.env`.
- **Solution**: The codebase now uses `ensure_env_loaded(override=True)` to guarantee values in `.env` take precedence. Always restart your server (`Ctrl+C` then re-run `mathlore-forge serve`) after updating `.env`.

### 2. Fine-Grained Personal Access Token (PAT) Scoping
- If your GitHub PAT starts with `github_pat_`, it is a fine-grained token.
- **Resource Owner**: If the repository is under the `mathlingua` organization, the token's **Resource owner** must be set to `mathlingua` (not your personal account), with permissions for `Contents: Read & write` and `Pull requests: Read & write`.
- **Alternative**: You can use a **Personal Access Token (Classic)** (`ghp_...`) with the `repo` scope at [github.com/settings/tokens](https://github.com/settings/tokens), which automatically works across all repositories and organizations you have access to.

### 3. "Review cannot be requested from pull request author" (HTTP 422)
- GitHub does not permit requesting a review from the user who authored the PR.
- Because the PR is created using your PAT, you are the author on GitHub.
- This is why commenting **`/forge approve`** or **`/forge merge`** is the standard way to land PRs.

### 4. The Web Dashboard shows 0 duration / 0 tokens while the agent is running
- Agent authoring tasks take between 1 to 2 minutes as the agent explores the repository, formulates definitions, runs `mlg check`, and formats code.
- During this window, the task status is **Running** (or **Planning**).
- Both the main dashboard and trajectory pages automatically poll and refresh themselves every few seconds until the run completes.
