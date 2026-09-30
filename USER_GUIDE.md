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
3. [Slash Commands Reference](#3-slash-commands-reference)
4. [Running Locally vs. Production on GCP](#4-running-locally-vs-production-on-gcp)
   - [Local Development Workflow](#local-development-workflow)
   - [Production Cloud Workflow](#production-cloud-workflow)
5. [Troubleshooting & Frequently Asked Questions](#5-troubleshooting--frequently-asked-questions)

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
            ▼ (Feedback Needed)                     ▼ (Approved!)
  Dominic leaves review comments         Dominic comments `/forge approve`
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

### Step 5: Approving & Landing the PR

When the PR is ready to be merged:

#### Option A: Comment `/forge approve` (Recommended)
On the PR conversation tab, leave a comment:
```
/forge approve
```
*(or `/forge merge`)*

> **Why this is recommended**: Because the PR was opened using your GitHub Personal Access Token, GitHub considers you the author of the Pull Request. GitHub's interface typically disables the native "Approve" button for the PR author (*"You cannot approve your own pull request"*). Commenting `/forge approve` works instantly and cleanly bypasses that restriction.

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

## 3. Slash Commands Reference

You can control Mathlore Forge directly from GitHub issue and PR comments using these commands:

| Command | Where to Use | Action |
| :--- | :--- | :--- |
| **`/forge address`** | PR Conversation | Instructs the agent to read all unresolved review comments, modify the code, re-test with `mlg`, and push a new commit. |
| **`/forge approve`** | PR Conversation | Approves the PR, executes the self-improvement flywheel (guidelines + golden test), and squash-merges the PR. |
| **`/forge merge`** | PR Conversation | Alias for `/forge approve`. |

---

## 4. Running Locally vs. Production on GCP

### Local Development Workflow

When working locally on your development machine:

```bash
# 1. Start the server (auto-reloads on code edits)
# DEV_ALLOW_LOCAL_ADMIN=true logs you in as Dominic Kramer automatically without OAuth setup
DEV_ALLOW_LOCAL_ADMIN=true uv run mathlore-forge serve --port 8080 --host 127.0.0.1 --reload

# Open http://localhost:8080 in your browser.
```

#### Triggering Local Tasks:

Because a local server running on `127.0.0.1:8080` cannot receive direct webhooks from GitHub without a reverse tunnel (like ngrok), you can trigger and test tasks locally using either of two methods:

**Method 1: Using the CLI Worker (Fastest & Easiest)**
```bash
# Test authoring for an issue
uv run mathlore-forge worker --repo mathlingua/mathlore --issue 1

# Test addressing review comments on a PR
uv run mathlore-forge worker --repo mathlingua/mathlore --pr 1

# Test the pre-merge flywheel and merge on a PR
uv run mathlore-forge worker --repo mathlingua/mathlore --flywheel-pr 1
```

**Method 2: Simulating a Webhook with `curl`**
```bash
# Simulate an issue opened webhook
curl -X POST http://127.0.0.1:8080/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issues" \
  -d '{
    "action": "opened",
    "issue": {
      "number": 1,
      "title": "[Forge] Add subset theorem",
      "body": "Add subset monotonicity theorem to 01_set_theory/04_operations.mlg",
      "user": {"login": "DominicKramer"},
      "labels": [{"name": "forge"}]
    },
    "sender": {"login": "DominicKramer"},
    "repository": {"full_name": "mathlingua/mathlore"}
  }'

# Simulate `/forge approve` comment on a PR
curl -X POST http://127.0.0.1:8080/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: issue_comment" \
  -d '{
    "action": "created",
    "issue": {
      "number": 1,
      "pull_request": {"url": "https://api.github.com/repos/mathlingua/mathlore/pulls/1"}
    },
    "comment": {
      "body": "/forge approve",
      "user": {"login": "DominicKramer"}
    },
    "repository": {"full_name": "mathlingua/mathlore"}
  }'
```

---

### Production Cloud Workflow

In production, Mathlore Forge runs on **Google Cloud Platform (Cloud Run)** provisioned via **Terraform**:
- **Automatic Webhooks**: GitHub delivers webhooks directly to your public Cloud Run HTTPS URL.
- **No Manual Intervention**: Commenting `/forge address` or `/forge approve` on GitHub works natively without running anything locally.
- **Secure Authentication**: The web dashboard is secured by Google OAuth 2.0 and strictly limited to `DominicKramer@gmail.com`.

For full step-by-step instructions on deploying to GCP, see [**`DEPLOYMENT.md`**](DEPLOYMENT.md).

---

## 5. Troubleshooting & Frequently Asked Questions

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
- During this window, the task status is **Running**.
- Both the main dashboard and trajectory pages automatically poll and refresh themselves every few seconds until the run completes.
