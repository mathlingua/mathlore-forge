# Mathlore Forge: Terraform Deployment, Operations, and Teardown Manual

Mathlore Forge uses **Terraform** as the single, industry-standard Infrastructure as Code (IaC) tool for provisioning, updating, and tearing down all Google Cloud Platform (GCP) resources.

This guide provides instructions for:
1. **Initial Deployment on GCP using Terraform** (including GitHub Webhook setup)
2. **Redeploying and Rolling Out Changes** (declarative zero-downtime updates and rollbacks)
3. **Tearing Down and Stopping Everything** (complete cleanup to eliminate all cloud costs)
4. **Local Development and Testing** (how to run and verify locally before deploying live)

---

## Infrastructure Overview

All infrastructure is defined declaratively under [`infra/terraform/`](infra/terraform/):
- **GCP APIs**: Automatically enabled via `google_project_service`.
- **IAM Service Account**: Least-privilege service account (`mathlore-forge-sa`) with permissions to access secrets, write logs, and export traces.
- **Secret Manager**: Secure secret slots for API keys and OAuth credentials.
- **Artifact Registry**: Docker repository storing versioned container images.
- **Cloud Run Service (`mathlore-forge-web`)**: Auto-scaling (0–5 instances) web dashboard and webhook receiver with health checks.
- **Cloud Run Job (`mathlore-forge-worker`)**: Dedicated agent execution worker for complex authoring tasks (default timeout: 10 minutes / 600s, easily increased via `worker_timeout`).

> [!TIP]
> **Recommended: Interactive Automated Deployment Script**
> We provide a guided, step-by-step deployment script [`deploy.sh`](deploy.sh) that implements this entire manual interactively:
> ```bash
> ./deploy.sh
> ```
> At each step, it prints clear instructions, prompts for your project credentials with sensible defaults, displays the exact commands about to run, and asks for your confirmation before executing them. It saves configuration state in `.deploy_config` so you can safely re-run it at any time to resume or update.

---

## Part 1: Initial Deployment Step-by-Step

Follow these steps when setting up Mathlore Forge on GCP for the first time.

### Step 1: Install & Authenticate CLI Tools
- **What to do**:
  ```bash
  # 1. Install Terraform (if not already installed)
  brew install terraform

  # 2. Authenticate gcloud CLI
  gcloud auth login
  gcloud auth application-default login
  ```
- **Why it is needed**:
  - `terraform` is the declarative engine that creates and manages your cloud resources.
  - `gcloud auth application-default login` creates Application Default Credentials (ADC) on your machine, allowing Terraform to authenticate with Google Cloud.

---

### Step 2: Set Your GCP Project and Region
- **What to do**:
  ```bash
  export GCP_PROJECT_ID="your-gcp-project-id"
  export GCP_REGION="us-central1"

  gcloud config set project "$GCP_PROJECT_ID"
  ```
- **Why it is needed**:
  Ensures that both the Google Cloud CLI and Terraform target your intended GCP project without accidental deployment to another account.

---

### Step 3: Configure Google OAuth 2.0 Credentials (for Web Dashboard)
- **What to do**:
  1. Open the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials).
  2. If you haven't configured the **OAuth consent screen** yet:
     - Go to **APIs & Services** > **OAuth consent screen**.
     - Select **External** (or **Internal** if using Google Workspace) and click **Create**.
     - Set **App name**: `Mathlore Forge`.
     - Set **User support email**: `DominicKramer@gmail.com`.
     - Set **Developer contact email**: `DominicKramer@gmail.com`.
     - Under **Test users**, add `DominicKramer@gmail.com`.
     - Click **Save and Continue**.
  3. Create the OAuth Client ID:
     - Go to **APIs & Services** > **Credentials**.
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
  The Mathlore Forge Web Dashboard displays real-time agent trajectories, reasoning thoughts, and controls. Google OAuth 2.0 ensures that **only DominicKramer@gmail.com** can log into the dashboard; any unauthorized Google account is blocked with HTTP 403 Forbidden. *(Once Terraform outputs your Cloud Run URL in Step 5, you will add your Cloud Run HTTPS URL to this redirect URI list).*

---

### Step 4: Generate a GitHub Personal Access Token (PAT)
- **What to do**:
  1. Open GitHub in your browser: **[GitHub Personal Access Tokens (Fine-grained)](https://github.com/settings/tokens?type=beta)** (or go to **Settings** > **Developer Settings** > **Personal access tokens** > **Fine-grained tokens**).
  2. Click **Generate new token**.
  3. Configure the token details:
     - **Token name**: `mathlore-forge-automation`
     - **Expiration**: Select your desired validity period (e.g. 90 days, 1 year, or custom).
     - **Resource owner**: Select `mathlingua` (or your personal account depending on organization ownership).
     - **Repository access**: Select **Only select repositories**:
       - `mathlingua/mathlore`
       - `mathlingua/mathlore-forge`
  4. Configure Permissions under **Repository permissions**:
     - **`Contents`**: Set to **Read and write** *(Needed to create and push feature branches and commits)*.
     - **`Pull requests`**: Set to **Read and write** *(Needed to open PRs, list review comments, reply to comment threads, and squash-merge approved PRs)*.
     - **`Issues`**: Set to **Read and write** *(Needed to read issue descriptions, post status updates, and close resolved issues)*.
     - **`Metadata`**: Automatically set to **Read-only** by GitHub.
     *(Leave all other permissions as "No access" to follow the principle of least privilege)*.
  5. Click **Generate token** and copy the generated token string (`github_pat_...`).

- **Why it is needed & how it is used**:
  The autonomous Mathlore Forge agents must programmatically interact with GitHub on your behalf:
  - It clones/fetches the repository.
  - It creates feature branches (`forge/issue-<num>-<slug>`).
  - It commits authored Mathlingua code and pushes to GitHub.
  - It opens Pull Requests, requests review from Dominic, replies to inline comments, and merges the PR once approved.
  - It opens self-improvement PRs in `mathlingua/mathlore-forge`.

- **How it is specified for Production vs. Local**:
  - **In Production**: You store this token in **GCP Secret Manager** (in Step 8). Terraform mounts this secret directly into Cloud Run (`mathlore-forge-web` and `mathlore-forge-worker`) as the `GITHUB_TOKEN` environment variable. The token is never checked into Git or baked into container images.
  - **In Local Development**: You paste this token into your local `mathlore-forge/.env` file:
    ```env
    GITHUB_TOKEN=github_pat_your_token_here
    ```

---

### Step 5: Build & Push the Initial Container Image
- **What to do**:
  Before Terraform provisions Cloud Run, an initial container image must exist in Artifact Registry:
  ```bash
  # 1. Enable Artifact Registry & Cloud Build APIs
  gcloud services enable artifactregistry.googleapis.com cloudbuild.googleapis.com

  # 2. Create the Artifact Registry Docker repository
  gcloud artifacts repositories create mathlore-forge \
    --repository-format=docker \
    --location="$GCP_REGION" 2>/dev/null || true

  # 3. Build and push container image using Cloud Build
  gcloud builds submit \
    --tag "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/mathlore-forge/app:latest" \
    -f infra/Dockerfile .
  ```
- **Why it is needed**:
  Cloud Run requires a container image to be present at creation time. Cloud Build compiles your code and dependencies in the cloud and pushes the image directly into Artifact Registry.

---

### Step 6: Provision Infrastructure with Terraform
- **What to do**:
  Navigate to the Terraform directory and apply:
  ```bash
  cd infra/terraform

  # 1. Initialize Terraform
  terraform init

  # 2. Preview infrastructure changes
  terraform plan -var="project_id=$GCP_PROJECT_ID" -var="region=$GCP_REGION"

  # 3. Apply and provision resources
  terraform apply -var="project_id=$GCP_PROJECT_ID" -var="region=$GCP_REGION"
  ```
- **Why it is needed**:
  Terraform declaratively provisions:
  1. All required GCP APIs.
  2. The dedicated IAM Service Account (`mathlore-forge-sa`) and its least-privilege roles.
  3. The Secret Manager secret slots.
  4. The Cloud Run Service (`mathlore-forge-web`) configured with auto-scaling (0 to 5) and startup health probes.
  5. Public invoker access so GitHub can deliver webhooks.
  6. The Cloud Run Job (`mathlore-forge-worker`) with a 10-minute execution timeout (configurable via `worker_timeout`).
  7. **Outputs your live Production URLs**:
     ```
     Outputs:
     artifact_registry_repository = "us-central1-docker.pkg.dev/your-project/mathlore-forge"
     dashboard_url = "https://mathlore-forge-web-abc123xyz-uc.a.run.app"
     service_account_email = "mathlore-forge-sa@your-project.iam.gserviceaccount.com"
     webhook_url = "https://mathlore-forge-web-abc123xyz-uc.a.run.app/webhooks/github"
     ```

---

### Step 7: Add Your Production Cloud Run Domain to Google OAuth
- **What to do**:
  Now that Cloud Run is deployed, you have your live production domain name (from the `dashboard_url` output above):

  1. If you didn't save the URL from the Terraform output, retrieve it anytime via:
     ```bash
     terraform output dashboard_url
     # Or via gcloud:
     gcloud run services describe mathlore-forge-web --region "$GCP_REGION" --format='value(status.url)'
     ```
     *(Example: `https://mathlore-forge-web-abc123xyz-uc.a.run.app`)*

  2. Return to the [Google Cloud Console Credentials Page](https://console.cloud.google.com/apis/credentials).
  3. Click on your OAuth 2.0 Client ID (**Mathlore Forge Web**) to edit it.
  4. Under **Authorized JavaScript origins**, click **+ ADD URI** and add your production URL:
     ```
     https://<YOUR-CLOUD-RUN-URL>
     ```
     *(e.g., `https://mathlore-forge-web-abc123xyz-uc.a.run.app`)*
  5. Under **Authorized redirect URIs**, click **+ ADD URI** and add:
     ```
     https://<YOUR-CLOUD-RUN-URL>/auth/callback
     ```
     *(e.g., `https://mathlore-forge-web-abc123xyz-uc.a.run.app/auth/callback`)*
  6. Click **SAVE**.

- **Why it is needed**:
  Google OAuth strictly rejects any login request where the redirect URI is not pre-registered in the Google Cloud Console. Because Cloud Run generates its default HTTPS domain upon first deployment, adding the production URL is a quick 30-second step that connects Google's identity servers to your newly deployed Cloud Run domain. *(Changes take effect immediately; no rebuilding or redeployment of Cloud Run is required).*

  > [!TIP] **Using a Custom Domain (Optional)**: If you map a custom domain (like `https://forge.mathlore.org`) to your Cloud Run service via Cloud Run Domain Mappings or Cloud Load Balancing, you can add `https://forge.mathlore.org/auth/callback` to the OAuth Authorized redirect URIs instead.

---

### Step 8: Populate Secret Values in Secret Manager
- **What to do**:
  Terraform created the secret resources in Step 6. Now, add the secret version payloads:

  ```bash
  # 1. Gemini API Key (for Google Antigravity Agent reasoning and authoring)
  echo -n "your-gemini-api-key" | gcloud secrets versions add GEMINI_API_KEY --data-file=-

  # 2. GitHub Token (from Step 4)
  echo -n "github_pat_your_token_from_step_4" | gcloud secrets versions add GITHUB_TOKEN --data-file=-

  # 3. GitHub Webhook Secret (Shared secret to verify webhook HMAC SHA-256 signatures)
  WEBHOOK_SECRET=$(openssl rand -hex 20)
  echo -n "$WEBHOOK_SECRET" | gcloud secrets versions add GITHUB_WEBHOOK_SECRET --data-file=-
  echo "Your GITHUB_WEBHOOK_SECRET is: $WEBHOOK_SECRET"

  # 4. Google OAuth Client ID & Secret (from Step 3)
  echo -n "your-client-id.apps.googleusercontent.com" | gcloud secrets versions add GOOGLE_CLIENT_ID --data-file=-
  echo -n "your-client-secret" | gcloud secrets versions add GOOGLE_CLIENT_SECRET --data-file=-

  # 5. Session Secret Key (Used to cryptographically sign session cookies)
  openssl rand -hex 32 | gcloud secrets versions add SESSION_SECRET_KEY --data-file=-
  ```

- **Why it is needed**:
  Separating secret definitions (managed in Terraform) from secret data values (populated via CLI) prevents sensitive credentials from ever being stored in plain text inside `.tf` files or Git repositories.

---

### Step 9: Configure the GitHub Webhook in `mathlore`
- **What to do**:
  1. Open your GitHub repository: **`https://github.com/mathlingua/mathlore/settings/hooks`**.
  2. Click **Add webhook**.
  3. Fill in the form fields:
     - **Payload URL**: Enter the `webhook_url` output by Terraform:
       ```
       https://<YOUR-CLOUD-RUN-URL>/webhooks/github
       ```
     - **Content type**: Select **`application/json`**.
     - **Secret**: Enter your `GITHUB_WEBHOOK_SECRET` string from Step 8.
     - **SSL verification**: Select **Enable SSL verification**.
     - **Which events would you like to trigger this webhook?**:
       - Choose **Let me select individual events**:
         - [x] **Issues** (triggers initial authoring on `[forge]` issues)
         - [x] **Pull requests** (tracks PR lifecycle)
         - [x] **Pull request reviews** (triggers review addressing or approval merge)
         - [x] **Issue comments** (enables `/forge address` and `/forge approve` comments)
     - **Active**: Check **Active**.
  4. Click **Add webhook**.
  5. *(Optional)* Repeat on `https://github.com/mathlingua/mathlore-forge/settings/hooks` so the flywheel can also receive comments on forge PRs.

- **Why it is needed**:
  Registers your Cloud Run service as the listener for repository events. GitHub sends an HTTP POST whenever you create an issue or leave a review. The webhook signature allows the Forge server to verify authenticity before launching any compute.

---

### Step 10: Verify the Live Deployment
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

When you update prompts, domain skills in `skills/`, compiler tooling, or web dashboard code, follow this procedure to roll out changes with zero downtime.

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

### Step 3: Roll Out the Revision with Terraform
- **What to do**:
  ```bash
  cd infra/terraform
  terraform apply \
    -var="project_id=$GCP_PROJECT_ID" \
    -var="region=$GCP_REGION" \
    -var="image_tag=$TAG"
  ```
- **Why it is needed**:
  Terraform updates both the Cloud Run Service (`mathlore-forge-web`) and the Cloud Run Job (`mathlore-forge-worker`) to reference the new container image tag.
  Cloud Run uses **zero-downtime blue/green deployments**:
  1. It starts a new container running the updated image.
  2. It performs a canary probe against `/healthz`.
  3. Only once the new container is healthy does Cloud Run switch 100% of live traffic to the new revision.

---

### Step 4: How to Roll Back Instantly (If Something Breaks)
- **What to do**:
  If a deployed change introduces a bug, re-apply Terraform with the previous known good commit tag:
  ```bash
  cd infra/terraform
  terraform apply \
    -var="project_id=$GCP_PROJECT_ID" \
    -var="region=$GCP_REGION" \
    -var="image_tag=$PREVIOUS_TAG"
  ```
- **Why it is needed**:
  Terraform declaratively rolls back Cloud Run to the previous image tag. The rollback completes in seconds without rebuilding.

---

## Part 3: Tearing Down and Stopping Everything

When you want to stop all running services, remove cloud infrastructure, or eliminate all ongoing GCP storage/compute costs, use Terraform to destroy the environment.

### Step 1: Run Terraform Destroy
- **What to do**:
  ```bash
  cd infra/terraform
  terraform destroy -var="project_id=$GCP_PROJECT_ID" -var="region=$GCP_REGION"
  ```
- **Why it is needed**:
  Terraform reads the state file and deletes all managed resources in reverse dependency order:
  - Stops and deletes the Cloud Run Service (`mathlore-forge-web`).
  - Stops and deletes the Cloud Run Job (`mathlore-forge-worker`).
  - Removes the IAM Service Account and project role bindings.
  - Deletes the Secret Manager secrets.
  - Deletes the Artifact Registry repository and all stored container images.
  This immediately terminates all ingress and stops all cloud costs.

---

### Step 2: Delete or Disable the GitHub Webhook
- **What to do**:
  1. Go to **`https://github.com/mathlingua/mathlore/settings/hooks`**.
  2. Click **Edit** next to the webhook URL.
  3. Scroll down and click **Delete webhook** (or uncheck **Active** to temporarily pause it).
- **Why it is needed**:
  Prevents GitHub from sending undeliverable HTTP requests to a destroyed Cloud Run service.

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
