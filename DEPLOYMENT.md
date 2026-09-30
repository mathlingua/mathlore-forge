# Mathlore Forge: Complete Deployment, Operations, and Teardown Manual

This document provides complete, step-by-step instructions for:
1. **Initial Deployment on Google Cloud Platform (GCP)** (including GitHub Webhook configuration)
2. **Redeploying and Rolling Out Changes** (zero-downtime updates and rollbacks)
3. **Tearing Down and Stopping Everything** (complete cleanup to eliminate all cloud costs)
4. **Local Development and Testing** (how to run and verify locally before deploying live)

Every step explains **WHAT** command or action to run, and **WHY** it is necessary for the system.

---

## Architecture Context

Mathlore Forge on GCP uses an event-driven architecture split into two decoupled runtimes:

```
GitHub (mathlore) ──[Webhook Event]──> Cloud Run Service (Web Dashboard & Webhook Receiver)
                                                │
                                                ▼ (Dispatches Task)
                                       Cloud Run Job (Mathlingua Authoring Worker)
                                                │ (Up to 24h Execution)
                                                ▼
                                       Antigravity Agent + mlg Compiler Engine
                                                │
                                                ▼
GitHub (mathlore) <──[Create PR / Update / Merge]┘
```

1. **Cloud Run Service (`mathlore-forge-web`)**:
   - Always available, receives GitHub webhooks in real time.
   - Hosts the Web Dashboard with Google OAuth 2.0 (restricted strictly to `DominicKramer@gmail.com`).
   - Streams live agent thoughts and compiler checks via Server-Sent Events (SSE).
   - Auto-scales to 0 instances when idle, incurring near-zero cost.
2. **Cloud Run Jobs (`mathlore-forge-worker`)**:
   - Dedicated task execution container for long-running AI authoring tasks.
   - Configured with a **24-hour timeout**, 2 vCPUs, and 4GB RAM.
   - Does not hold open HTTP connections; executes to completion and terminates.

---

## Part 1: Initial Deployment Step-by-Step

Follow these steps when setting up Mathlore Forge on GCP for the first time.

### Step 1: Install & Authenticate the `gcloud` CLI
- **What to do**:
  ```bash
  gcloud auth login
  gcloud auth application-default login
  ```
- **Why it is needed**:
  Authenticates your local terminal with Google Cloud. `gcloud auth login` authorizes the command-line tool to manage cloud resources on your behalf, and `application-default login` provides Application Default Credentials (ADC) for deploying services and accessing secrets.

---

### Step 2: Set Your GCP Project and Region
- **What to do**:
  ```bash
  export GCP_PROJECT_ID="your-gcp-project-id"
  export GCP_REGION="us-central1"

  gcloud config set project "$GCP_PROJECT_ID"
  ```
- **Why it is needed**:
  All GCP resources (Cloud Run, Secret Manager, Artifact Registry) belong to a specific Project ID and geographic Region. Setting these environment variables ensures all subsequent commands target the correct project without accidental deployment to another account.

---

### Step 3: Enable the Required GCP Service APIs
- **What to do**:
  ```bash
  gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    logging.googleapis.com \
    cloudtrace.googleapis.com
  ```
- **Why it is needed**:
  By default, new GCP projects have most APIs disabled. Each enabled API provides an essential building block:
  - `run.googleapis.com`: Enables Google Cloud Run (Services and Jobs) to run our Docker containers.
  - `artifactregistry.googleapis.com`: Enables Artifact Registry to store our versioned Docker container images.
  - `cloudbuild.googleapis.com`: Enables Cloud Build to compile our Dockerfile in the cloud without needing Docker installed locally.
  - `secretmanager.googleapis.com`: Enables Secret Manager to securely inject API keys and OAuth credentials into Cloud Run without baking them into container images or code.
  - `logging.googleapis.com` & `cloudtrace.googleapis.com`: Enables structured logging and OpenTelemetry distributed tracing.

---

### Step 4: Configure Google OAuth 2.0 Credentials (for Web Dashboard)
- **What to do**:
  1. Open the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials).
  2. If you haven't configured the **OAuth consent screen** yet:
     - Navigate to **APIs & Services** > **OAuth consent screen**.
     - Choose **External** (or **Internal** if using Google Workspace) and click **Create**.
     - Set **App name**: `Mathlore Forge`.
     - Set **User support email**: `DominicKramer@gmail.com`.
     - Set **Developer contact email**: `DominicKramer@gmail.com`.
     - Under **Test users**, add `DominicKramer@gmail.com`.
     - Click **Save and Continue**.
  3. Create the OAuth Client ID:
     - Navigate to **APIs & Services** > **Credentials**.
     - Click **+ CREATE CREDENTIALS** > **OAuth client ID**.
     - Application type: Select **Web application**.
     - Name: `Mathlore Forge Web`.
     - Under **Authorized JavaScript origins**, add:
       - `http://localhost:8080` (for local development)
       - `http://127.0.0.1:8080` (for local development)
     - Under **Authorized redirect URIs**, add:
       - `http://localhost:8080/auth/callback`
       - `http://127.0.0.1:8080/auth/callback`
     - Click **CREATE**.
  4. Note down the **Client ID** and **Client Secret** displayed in the popup.
- **Why it is needed**:
  The Mathlore Forge Web Dashboard displays real-time agent trajectories, reasoning thoughts, and controls (stop, restart, retry). Google OAuth 2.0 ensures that **only DominicKramer@gmail.com** can log into the dashboard; any unauthorized Google account is blocked with HTTP 403 Forbidden. *(Note: Once deployed to Cloud Run in Step 6, you will add your Cloud Run HTTPS URL to the authorized redirect URIs list).*

---

### Step 5: Store Secrets in GCP Secret Manager
- **What to do**:
  Run the following commands to create each secret:

  ```bash
  # 1. Gemini API Key (for Google Antigravity Agent reasoning and authoring)
  gcloud secrets create GEMINI_API_KEY --replication-policy="automatic"
  echo -n "your-gemini-api-key" | gcloud secrets versions add GEMINI_API_KEY --data-file=-

  # 2. GitHub Token (Personal Access Token or GitHub App Token for PRs and comments)
  gcloud secrets create GITHUB_TOKEN --replication-policy="automatic"
  echo -n "your-github-token" | gcloud secrets versions add GITHUB_TOKEN --data-file=-

  # 3. GitHub Webhook Secret (Shared secret to verify webhook HMAC SHA-256 signatures)
  gcloud secrets create GITHUB_WEBHOOK_SECRET --replication-policy="automatic"
  openssl rand -hex 20 | gcloud secrets versions add GITHUB_WEBHOOK_SECRET --data-file=-

  # 4. Google OAuth Client ID & Secret (from Step 4)
  gcloud secrets create GOOGLE_CLIENT_ID --replication-policy="automatic"
  echo -n "your-client-id.apps.googleusercontent.com" | gcloud secrets versions add GOOGLE_CLIENT_ID --data-file=-

  gcloud secrets create GOOGLE_CLIENT_SECRET --replication-policy="automatic"
  echo -n "your-client-secret" | gcloud secrets versions add GOOGLE_CLIENT_SECRET --data-file=-

  # 5. Session Secret Key (Used to cryptographically sign session cookies)
  gcloud secrets create SESSION_SECRET_KEY --replication-policy="automatic"
  openssl rand -hex 32 | gcloud secrets versions add SESSION_SECRET_KEY --data-file=-
  ```

- **Why it is needed**:
  Cloud Run mounts these secrets directly as environment variables at container startup. This keeps credentials completely out of Git history and container layers.
  - `GEMINI_API_KEY`: Required by the Google Antigravity harness to call Gemini models (`gemini-3.8-flash`).
  - `GITHUB_TOKEN`: Required by [`GitHubClient`](file:///Users/kramer/Developer/mathlingua/mathlore-forge/src/mathlore_forge/workflows/github_client.py) to create branches, push commits, open PRs, reply to review comments, and merge PRs.
  - `GITHUB_WEBHOOK_SECRET`: Required to cryptographically verify (`X-Hub-Signature-256`) that incoming webhook requests originate from GitHub and not an unauthorized third party.
  - `GOOGLE_CLIENT_ID` & `GOOGLE_CLIENT_SECRET`: Required by the Google OAuth flow to exchange the authentication code for Dominic's email.
  - `SESSION_SECRET_KEY`: Used by `itsdangerous` to sign the browser session cookie so authentication cannot be forged.

---

### Step 6: Deploy Services using `./infra/deploy.sh`
- **What to do**:
  Run the automated deployment script from the `mathlore-forge` root directory:
  ```bash
  ./infra/deploy.sh
  ```
- **Why it is needed**:
  This script executes the cloud build and deployment steps:
  1. Checks if the Artifact Registry repository (`mathlore-forge`) exists; creates it if missing.
  2. Uses **Cloud Build** to build [`infra/Dockerfile`](file:///Users/kramer/Developer/mathlingua/mathlore-forge/infra/Dockerfile) and pushes the container image to Artifact Registry.
  3. Deploys **Cloud Run Service (`mathlore-forge-web`)**:
     - Configures port 8080 and automatic HTTPS.
     - Sets environment variables: `ALLOWED_ADMIN_EMAIL=DominicKramer@gmail.com` and `ALLOWED_GITHUB_AUTHOR=DominicKramer`.
     - Binds the 6 secrets from Secret Manager.
     - Configures autoscaling from 0 to 5 instances (idle instances scale to 0 to save costs).
  4. Deploys **Cloud Run Job (`mathlore-forge-worker`)**:
     - Configures the long-running worker container with `mathlore-forge worker`.
     - Allocates 2 vCPUs and 4GB RAM.
     - Sets a **24-hour execution timeout** so long agent authoring sessions are never prematurely killed.
  5. Prints the public URL:
     ```
     ==================================================
     ✔ Deployment Successful!
     Dashboard & Webhook URL: https://mathlore-forge-web-xyz-uc.a.run.app
     GitHub Webhook Target:   https://mathlore-forge-web-xyz-uc.a.run.app/webhooks/github
     ==================================================
     ```

- **Important follow-up**:
  Copy the `Dashboard URL` (e.g., `https://mathlore-forge-web-xyz-uc.a.run.app`) and add it to your Google OAuth Client ID in Google Cloud Console:
  - Add to **Authorized JavaScript origins**: `https://mathlore-forge-web-xyz-uc.a.run.app`
  - Add to **Authorized redirect URIs**: `https://mathlore-forge-web-xyz-uc.a.run.app/auth/callback`

---

### Step 7: Configure the GitHub Webhook in `mathlore`
- **What to do**:
  1. Open your GitHub repository: **`https://github.com/mathlingua/mathlore/settings/hooks`**.
  2. Click the **Add webhook** button.
  3. Fill in the form fields:
     - **Payload URL**: Enter your Cloud Run webhook URL:
       ```
       https://<YOUR-CLOUD-RUN-URL>/webhooks/github
       ```
     - **Content type**: Select **`application/json`** *(do not leave as application/x-www-form-urlencoded)*.
     - **Secret**: Retrieve your secret value from Secret Manager:
       ```bash
       gcloud secrets versions access latest --secret=GITHUB_WEBHOOK_SECRET
       ```
       Paste this string into the **Secret** field.
     - **SSL verification**: Select **Enable SSL verification**.
     - **Which events would you like to trigger this webhook?**:
       - Choose **Let me select individual events**:
         - [x] **Issues** (triggers initial authoring on `[forge]` issues)
         - [x] **Pull requests** (tracks PR lifecycle)
         - [x] **Pull request reviews** (triggers review addressing or approval merge)
         - [x] **Issue comments** (enables `/forge address` and `/forge approve` comments)
     - **Active**: Check **Active**.
  4. Click **Add webhook**.
  5. *(Optional)* Repeat the same step on `https://github.com/mathlingua/mathlore-forge/settings/hooks` so the self-improvement flywheel can also receive comments on forge PRs.

- **Why it is needed**:
  This registers your Cloud Run service as the listener for repository events. GitHub sends an HTTP POST to this endpoint whenever Dominic opens an issue, submits a review, or comments. The webhook signature allows the Forge server to verify authenticity before launching any compute.

---

### Step 8: Verify the Live Deployment
- **What to do**:
  1. **Check health endpoint**:
     ```bash
     curl -i https://<YOUR-CLOUD-RUN-URL>/healthz
     ```
     Should return HTTP 200: `{"status":"healthy","service":"mathlore-forge"}`.
  2. **Visit the dashboard**:
     Open `https://<YOUR-CLOUD-RUN-URL>/` in your browser.
     - Click **Sign in with Google**.
     - Log in with `DominicKramer@gmail.com`.
     - You should see the dashboard with 0 active runs.
  3. **Test triggering an agent**:
     - Create an issue on `mathlingua/mathlore` titled: `[Forge] Test Authoring Connection` with label `forge`.
     - Refresh your dashboard: within seconds, the run appears with status **Running**.
     - Click **Trajectory** to view live streaming thoughts and compiler checks!

---

## Part 2: Redeploying and Rolling Out Changes

When you modify prompts, domain skills in `skills/`, compiler tooling, or web dashboard code, follow this procedure to roll out changes with zero downtime.

### Step 1: Commit Your Changes & Generate a Version Tag
- **What to do**:
  ```bash
  git commit -am "Update authoring prompt guidelines"
  TAG=$(git rev-parse --short HEAD)
  IMAGE="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/mathlore-forge/app:${TAG}"
  ```
- **Why it is needed**:
  Using a unique tag (the Git commit SHA) instead of `:latest` provides complete traceability. If any regression occurs, you know exactly which commit caused it and can roll back to a prior tag in seconds.

---

### Step 2: Build the Container Image
- **What to do**:
  ```bash
  gcloud builds submit --tag "$IMAGE" -f infra/Dockerfile .
  ```
- **Why it is needed**:
  Cloud Build compiles the Python code, synchronizes dependencies via `uv`, packages domain skills, and stores the immutable image in Artifact Registry.

---

### Step 3: Deploy the New Revision to Cloud Run Service
- **What to do**:
  ```bash
  gcloud run deploy mathlore-forge-web \
    --image "$IMAGE" \
    --region "$GCP_REGION"
  ```
- **Why it is needed**:
  Cloud Run uses **zero-downtime blue/green deployments**:
  1. It starts a container running the new revision.
  2. It performs a canary probe against `/healthz`.
  3. Only once the new container is healthy does Cloud Run switch 100% of live traffic to the new revision. Existing in-flight webhook requests finish gracefully on the old container.

---

### Step 4: Update the Cloud Run Job (Worker)
- **What to do**:
  ```bash
  gcloud run jobs update mathlore-forge-worker \
    --image "$IMAGE" \
    --region "$GCP_REGION"
  ```
- **Why it is needed**:
  Cloud Run Jobs run independently of the web service. Updating the job definition guarantees that the next time an agent task is triggered, it executes using the new container image with updated skills and tools.

---

### Step 5: How to Roll Back Instantly (If Something Breaks)
- **What to do**:
  If the new deployment has an issue:
  1. List prior revisions:
     ```bash
     gcloud run revisions list --service mathlore-forge-web --region "$GCP_REGION"
     ```
  2. Route 100% of traffic back to the previous healthy revision:
     ```bash
     gcloud run services update-traffic mathlore-forge-web \
       --region "$GCP_REGION" \
       --to-revisions "<PREVIOUS_REVISION_NAME>=100"
     ```
- **Why it is needed**:
  Cloud Run keeps all previous revisions stored and ready. Traffic shifting takes less than 1 second, with no rebuilding required.

---

## Part 3: Tearing Down and Stopping Everything

When you want to stop all running services, remove cloud infrastructure, or eliminate all ongoing GCP storage/compute costs, follow this section.

### Option A: Automated Teardown Script (Recommended)
Run:
```bash
./infra/teardown.sh
```
The script will prompt for confirmation and cleanly delete:
1. Cloud Run Service (`mathlore-forge-web`)
2. Cloud Run Job (`mathlore-forge-worker`)
3. Artifact Registry repository and all stored container images
4. (Optional) Secrets stored in Secret Manager

---

### Option B: Manual Step-by-Step Teardown

If you prefer to run the teardown commands manually:

#### 1. Delete the Cloud Run Service
- **Command**:
  ```bash
  gcloud run services delete mathlore-forge-web --region "$GCP_REGION" --quiet
  ```
- **Why it is needed**:
  Stops the web dashboard and terminates the public webhook endpoint. Ingress traffic ceases immediately.

#### 2. Delete the Cloud Run Job
- **Command**:
  ```bash
  gcloud run jobs delete mathlore-forge-worker --region "$GCP_REGION" --quiet
  ```
- **Why it is needed**:
  Removes the long-running worker definition so no new agent executions can be dispatched.

#### 3. Delete the Artifact Registry Repository
- **Command**:
  ```bash
  gcloud artifacts repositories delete mathlore-forge --location "$GCP_REGION" --quiet
  ```
- **Why it is needed**:
  Artifact Registry charges a nominal monthly fee for storing Docker image layers. Deleting the repository deletes all uploaded image versions and eliminates all storage costs.

#### 4. Remove Secrets from Secret Manager (Optional)
- **Command**:
  ```bash
  for SECRET in GEMINI_API_KEY GITHUB_TOKEN GITHUB_WEBHOOK_SECRET GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET SESSION_SECRET_KEY; do
    gcloud secrets delete "$SECRET" --quiet
  done
  ```
- **Why it is needed**:
  Removes all stored credentials from GCP if you want a complete wipe of the environment.

#### 5. Disable or Delete the GitHub Webhook
- **Action**:
  1. Go to **`https://github.com/mathlingua/mathlore/settings/hooks`**.
  2. Click **Edit** next to the webhook URL.
  3. Scroll down and click **Delete webhook** (or uncheck **Active** to temporarily pause it).
- **Why it is needed**:
  If the Cloud Run service is deleted but GitHub continues sending webhooks, GitHub will log failed delivery attempts (HTTP 404). Disabling or deleting the webhook prevents unnecessary delivery attempts.

---

## Part 4: Running Locally (Try Before Rollout)

You can run and test everything locally on your machine before deploying to GCP.

### 1. Set Up Local `.env`
In `mathlore-forge/.env`:
```env
GEMINI_API_KEY=your-gemini-api-key
ALLOWED_ADMIN_EMAIL=DominicKramer@gmail.com
ALLOWED_GITHUB_AUTHOR=DominicKramer
GITHUB_TOKEN=your-github-token

# Instant local admin bypass without Google OAuth keys:
DEV_ALLOW_LOCAL_ADMIN=true
```

### 2. Start the Local Server
```bash
uv run mathlore-forge serve --port 8080 --host 127.0.0.1 --reload
```
Open **`http://localhost:8080`** in your browser. Click **Sign in with Google** to enter the dashboard.

### 3. Test Agent Workflows via CLI or Dashboard
- **From Dashboard**: Click **Trigger Manual Run**, enter issue `42`, click Start.
- **From CLI**:
  ```bash
  uv run mathlore-forge worker --repo mathlingua/mathlore --issue 42
  ```

### 4. Run the Full Test Suite
```bash
uv run pytest
```
```bash
uv run mlg-golden run --agent simulated
```
