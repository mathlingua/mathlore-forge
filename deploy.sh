#!/usr/bin/env bash
# ==============================================================================
# Mathlore Forge: Interactive Step-by-Step GCP & Terraform Deployment Script
#
# This script guides you through the complete deployment of Mathlore Forge to
# Google Cloud Platform (Cloud Run, Secret Manager, Artifact Registry, Terraform).
#
# Features:
# - Step-by-step interactive workflow with clear explanations
# - Prompts for necessary inputs with sensible defaults and .env integration
# - Previews every command before running and asks for your confirmation [Y/n/s]
# - Fully idempotent and safely re-runnable after resolving any errors
# - Saves configuration state in .deploy_config (chmod 600, gitignored)
# - Masks sensitive API keys and tokens in command preview displays
# ==============================================================================

set -uo pipefail

# Resolve repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CONFIG_FILE="${SCRIPT_DIR}/.deploy_config"
AUTO_APPROVE=false

# ANSI Terminal Colors
COLOR_RESET="\033[0m"
COLOR_BOLD="\033[1m"
COLOR_DIM="\033[2m"
COLOR_GREEN="\033[32m"
COLOR_CYAN="\033[36m"
COLOR_YELLOW="\033[33m"
COLOR_RED="\033[31m"
COLOR_MAGENTA="\033[35m"
COLOR_BLUE="\033[34m"

# Parse optional flags
for arg in "$@"; do
    case "$arg" in
        -y|--yes|--non-interactive)
            AUTO_APPROVE=true
            ;;
        -h|--help)
            echo "Usage: ./deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -y, --yes          Automatically approve all commands without prompting."
            echo "  -h, --help         Show this help message and exit."
            echo ""
            echo "Mathlore Forge Deployment Script will guide you step by step."
            echo "You can re-run this script safely at any time to resume or update."
            exit 0
            ;;
    esac
done

# ==============================================================================
# Helper Functions
# ==============================================================================

print_banner() {
    echo -e "${COLOR_BOLD}${COLOR_CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                   MATHLORE FORGE DEPLOYMENT                          ║"
    echo "║          Interactive Step-by-Step Production Setup                   ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo -e "${COLOR_RESET}"
    echo -e "Welcome! This script will guide you through setting up ${COLOR_BOLD}Mathlore Forge${COLOR_RESET} on GCP."
    echo -e "• At each step, you will be shown the ${COLOR_BOLD}exact commands${COLOR_RESET} about to run."
    echo -e "• You will be prompted to ${COLOR_BOLD}confirm, skip, or edit${COLOR_RESET} before execution."
    echo -e "• State is saved to ${COLOR_CYAN}.deploy_config${COLOR_RESET}, so if an error occurs, you can"
    echo -e "  fix it and ${COLOR_BOLD}safely re-run ./deploy.sh${COLOR_RESET} to resume where you left off."
    echo ""
}

print_step() {
    local step_num="$1"
    local step_title="$2"
    echo ""
    echo -e "${COLOR_BOLD}${COLOR_MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${COLOR_RESET}"
    echo -e "${COLOR_BOLD}${COLOR_CYAN}  Step ${step_num}: ${step_title}${COLOR_RESET}"
    echo -e "${COLOR_BOLD}${COLOR_MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${COLOR_RESET}"
    echo ""
}

print_info() {
    echo -e "  ${COLOR_DIM}ℹ ${1}${COLOR_RESET}"
}

print_success() {
    echo -e "  ${COLOR_GREEN}✔ ${1}${COLOR_RESET}"
}

print_warning() {
    echo -e "  ${COLOR_YELLOW}⚠ ${1}${COLOR_RESET}"
}

print_error() {
    echo -e "  ${COLOR_RED}✘ ${1}${COLOR_RESET}"
}

# Previews and prompts before executing any command
confirm_run() {
    local cmd="$1"
    local display_cmd="${2:-$cmd}"

    echo ""
    echo -e "  ${COLOR_DIM}┌── Command to execute ───────────────────────────────────────┐${COLOR_RESET}"
    echo -e "  ${COLOR_BOLD}${COLOR_CYAN}${display_cmd}${COLOR_RESET}"
    echo -e "  ${COLOR_DIM}└─────────────────────────────────────────────────────────────┘${COLOR_RESET}"

    if [ "$AUTO_APPROVE" = "true" ]; then
        echo -e "  ${COLOR_YELLOW}Auto-approving execution (--yes mode)...${COLOR_RESET}"
        eval "$cmd"
        return $?
    fi

    while true; do
        read -r -p "$(echo -e "  ${COLOR_BOLD}Run this command? [Y/n/s(skip)/q(quit)]: ${COLOR_RESET}")" choice
        case "$choice" in
            [Yy]|"")
                echo ""
                if eval "$cmd"; then
                    echo -e "  ${COLOR_GREEN}✔ Command succeeded.${COLOR_RESET}"
                    return 0
                else
                    local exit_code=$?
                    echo ""
                    print_error "Command failed with exit code ${exit_code}."
                    echo ""
                    while true; do
                        read -r -p "$(echo -e "  ${COLOR_YELLOW}Options: [r]etry command, [s]kip step, [a]bort script: ${COLOR_RESET}")" on_err
                        case "$on_err" in
                            [Rr])
                                echo ""
                                echo -e "  ${COLOR_YELLOW}Retrying command...${COLOR_RESET}"
                                if eval "$cmd"; then
                                    echo -e "  ${COLOR_GREEN}✔ Command succeeded.${COLOR_RESET}"
                                    return 0
                                else
                                    local retry_code=$?
                                    print_error "Retry failed with exit code ${retry_code}."
                                fi
                                ;;
                            [Ss])
                                print_warning "Skipped step by user request."
                                return 0
                                ;;
                            [Aa]|*)
                                echo ""
                                print_warning "Deployment paused."
                                echo -e "  ${COLOR_CYAN}💡 You can ask for assistance to resolve the error above.${COLOR_RESET}"
                                echo -e "  ${COLOR_CYAN}   When ready, simply run ./deploy.sh again to resume!${COLOR_RESET}"
                                echo ""
                                exit $exit_code
                                ;;
                        esac
                    done
                fi
                ;;
            [Nn]|[Qq])
                echo ""
                print_warning "Deployment paused by user."
                echo -e "  ${COLOR_CYAN}💡 You can resume anytime by running ./deploy.sh.${COLOR_RESET}"
                echo ""
                exit 0
                ;;
            [Ss])
                print_warning "Skipped step by user request."
                return 0
                ;;
            *)
                echo "  Please enter Y (yes), n (pause/quit), s (skip), or q (quit)."
                ;;
        esac
    done
}

# Prompt user for variable with default value
prompt_var() {
    local var_name="$1"
    local prompt_text="$2"
    local default_val="$3"
    local is_secret="${4:-false}"

    local current_val="${!var_name:-}"
    if [ -z "$current_val" ]; then
        current_val="$default_val"
    fi

    if [ "$is_secret" = "true" ]; then
        if [ -n "$current_val" ]; then
            local suffix="${current_val: -4}"
            echo -e "  ${COLOR_BOLD}${prompt_text}${COLOR_RESET} [currently configured: ****${suffix}]"
        else
            echo -e "  ${COLOR_BOLD}${prompt_text}${COLOR_RESET}"
        fi
        read -r -s -p "$(echo -e "  Enter value (leave blank to keep current): ")" input_val
        echo ""
    else
        if [ -n "$current_val" ]; then
            read -r -p "$(echo -e "  ${COLOR_BOLD}${prompt_text}${COLOR_RESET} [default: ${COLOR_CYAN}${current_val}${COLOR_RESET}]: ")" input_val
        else
            read -r -p "$(echo -e "  ${COLOR_BOLD}${prompt_text}${COLOR_RESET}: ")" input_val
        fi
    fi

    if [ -n "$input_val" ]; then
        eval "$var_name=\"\$input_val\""
    elif [ -n "$current_val" ]; then
        eval "$var_name=\"\$current_val\""
    fi
}

load_config() {
    # 1. Load from saved deployment config if it exists
    if [ -f "$CONFIG_FILE" ]; then
        # shellcheck disable=SC1090
        source "$CONFIG_FILE"
    fi

    # 2. Fallback to local .env file for unset values
    if [ -f ".env" ]; then
        if [ -z "${GEMINI_API_KEY:-}" ]; then
            GEMINI_API_KEY=$(grep -E '^GEMINI_API_KEY=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        fi
        if [ -z "${GITHUB_TOKEN:-}" ]; then
            GITHUB_TOKEN=$(grep -E '^GITHUB_TOKEN=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        fi
        if [ -z "${GOOGLE_CLIENT_ID:-}" ]; then
            GOOGLE_CLIENT_ID=$(grep -E '^GOOGLE_CLIENT_ID=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        fi
        if [ -z "${GOOGLE_CLIENT_SECRET:-}" ]; then
            GOOGLE_CLIENT_SECRET=$(grep -E '^GOOGLE_CLIENT_SECRET=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        fi
        if [ -z "${GITHUB_WEBHOOK_SECRET:-}" ]; then
            GITHUB_WEBHOOK_SECRET=$(grep -E '^GITHUB_WEBHOOK_SECRET=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        fi
        if [ -z "${ALLOWED_ADMIN_EMAIL:-}" ]; then
            ALLOWED_ADMIN_EMAIL=$(grep -E '^ALLOWED_ADMIN_EMAIL=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        fi
        if [ -z "${ALLOWED_GITHUB_AUTHOR:-}" ]; then
            ALLOWED_GITHUB_AUTHOR=$(grep -E '^ALLOWED_GITHUB_AUTHOR=' .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" || true)
        fi
    fi

    # Defaults
    ALLOWED_ADMIN_EMAIL="${ALLOWED_ADMIN_EMAIL:-DominicKramer@gmail.com}"
    ALLOWED_GITHUB_AUTHOR="${ALLOWED_GITHUB_AUTHOR:-DominicKramer}"
    GCP_REGION="${GCP_REGION:-us-central1}"
    IMAGE_TAG="${IMAGE_TAG:-latest}"
    WORKER_TIMEOUT="${WORKER_TIMEOUT:-600s}"
    TF_CMD="${TF_CMD:-terraform}"
}

save_config() {
    cat <<EOF > "$CONFIG_FILE"
# Mathlore Forge Deployment Configuration
# Generated on $(date)
GCP_PROJECT_ID="${GCP_PROJECT_ID:-}"
GCP_REGION="${GCP_REGION:-us-central1}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
WORKER_TIMEOUT="${WORKER_TIMEOUT:-600s}"
TF_CMD="${TF_CMD:-terraform}"
ALLOWED_ADMIN_EMAIL="${ALLOWED_ADMIN_EMAIL:-DominicKramer@gmail.com}"
ALLOWED_GITHUB_AUTHOR="${ALLOWED_GITHUB_AUTHOR:-DominicKramer}"
GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-}"
GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
GITHUB_WEBHOOK_SECRET="${GITHUB_WEBHOOK_SECRET:-}"
SESSION_SECRET_KEY="${SESSION_SECRET_KEY:-}"
EOF
    chmod 600 "$CONFIG_FILE"
}

# ==============================================================================
# Main Workflow
# ==============================================================================

print_banner
load_config

# ------------------------------------------------------------------------------
# STEP 1: Verify Prerequisites & Authentication
# ------------------------------------------------------------------------------
print_step "1" "Verify CLI Tools & Authentication"
print_info "Checking required CLI binaries (gcloud, git, openssl, curl)..."

MISSING_TOOLS=()
for tool in gcloud git openssl curl; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        MISSING_TOOLS+=("$tool")
    fi
done

if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    print_error "Missing required CLI tool(s): ${MISSING_TOOLS[*]}"
    echo "  Please install missing tools before continuing:"
    echo "  • Google Cloud SDK: brew install --cask google-cloud-sdk"
    exit 1
fi

# Detect Terraform or OpenTofu
TF_CMD=""
if command -v terraform >/dev/null 2>&1; then
    TF_CMD="terraform"
elif command -v tofu >/dev/null 2>&1; then
    TF_CMD="tofu"
fi

if [ -z "$TF_CMD" ]; then
    print_warning "Neither Terraform nor OpenTofu is currently installed."
    if command -v brew >/dev/null 2>&1; then
        echo -e "  ${COLOR_CYAN}Homebrew is available on your machine.${COLOR_RESET}"
        echo -e "  Terraform can be installed via HashiCorp's official tap:"
        echo -e "    ${COLOR_BOLD}brew tap hashicorp/tap && brew install hashicorp/tap/terraform${COLOR_RESET}"
        echo ""
        read -r -p "$(echo -e "  ${COLOR_BOLD}Would you like this script to install Terraform now? [Y/n]: ${COLOR_RESET}")" install_tf
        case "$install_tf" in
            [Yy]|"")
                confirm_run "brew tap hashicorp/tap && brew install hashicorp/tap/terraform"
                if command -v terraform >/dev/null 2>&1; then
                    TF_CMD="terraform"
                    print_success "Terraform installed successfully!"
                fi
                ;;
            *)
                echo -e "  You can install Terraform manually using either:"
                echo -e "  • Official tap: ${COLOR_CYAN}brew tap hashicorp/tap && brew install hashicorp/tap/terraform${COLOR_RESET}"
                echo -e "  • OpenTofu (drop-in open source tool): ${COLOR_CYAN}brew install opentofu${COLOR_RESET}"
                exit 1
                ;;
        esac
    fi
fi

if [ -z "$TF_CMD" ]; then
    print_error "Terraform or OpenTofu is required to proceed."
    echo "  Please install using one of the following commands, then re-run ./deploy.sh:"
    echo "  • brew tap hashicorp/tap && brew install hashicorp/tap/terraform"
    echo "  • brew install opentofu"
    exit 1
fi
print_success "Infrastructure IaC tool: ${TF_CMD} ($(command -v "$TF_CMD"))"
print_success "All required CLI tools are present."

# Verify gcloud authentication
print_info "Verifying gcloud user authentication..."
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
if [ -z "$ACTIVE_ACCOUNT" ]; then
    print_warning "No active gcloud account detected. Logging in..."
    confirm_run "gcloud auth login"
else
    print_success "Authenticated as: ${ACTIVE_ACCOUNT}"
fi

# Verify Application Default Credentials (needed by Terraform)
print_info "Verifying Application Default Credentials (ADC) for Terraform..."
if ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
    print_warning "Terraform requires Application Default Credentials to manage GCP resources."
    confirm_run "gcloud auth application-default login"
else
    print_success "Application Default Credentials (ADC) are valid."
fi

# ------------------------------------------------------------------------------
# STEP 2: Configure GCP Project and Region
# ------------------------------------------------------------------------------
print_step "2" "Select GCP Project & Region"
CURRENT_GCP_PROJECT=$(gcloud config get-value project 2>/dev/null || true)

prompt_var "GCP_PROJECT_ID" "GCP Project ID" "${CURRENT_GCP_PROJECT:-}"
if [ -z "$GCP_PROJECT_ID" ]; then
    print_error "GCP Project ID cannot be empty."
    exit 1
fi

prompt_var "GCP_REGION" "GCP Region" "${GCP_REGION:-us-central1}"
save_config

print_info "Setting active project in gcloud..."
confirm_run "gcloud config set project '${GCP_PROJECT_ID}'"

print_info "Ensuring core Resource Manager and Service Usage APIs are enabled..."
confirm_run "gcloud services enable serviceusage.googleapis.com cloudresourcemanager.googleapis.com"

# ------------------------------------------------------------------------------
# STEP 3: Google OAuth 2.0 Credentials (for Web Dashboard)
# ------------------------------------------------------------------------------
print_step "3" "Google OAuth 2.0 Credentials"
echo -e "  The Mathlore Forge Web Dashboard displays real-time agent trajectories"
echo -e "  and compiler telemetry. Google OAuth 2.0 ensures that ${COLOR_BOLD}only ${ALLOWED_ADMIN_EMAIL}${COLOR_RESET}"
echo -e "  can access it; all other accounts are rejected with HTTP 403 Forbidden."
echo ""
echo -e "  ${COLOR_BOLD}To configure in Google Cloud Console:${COLOR_RESET}"
echo -e "  1. Open: ${COLOR_CYAN}https://console.cloud.google.com/apis/credentials?project=${GCP_PROJECT_ID}${COLOR_RESET}"
echo -e "  2. If OAuth consent screen is not configured:"
echo -e "     • User Type: Select ${COLOR_BOLD}External${COLOR_RESET}"
echo -e "       ${COLOR_DIM}(Internal requires Google Workspace; External supports @gmail.com and${COLOR_RESET}"
echo -e "       ${COLOR_DIM} keeps the app in private 'Testing' mode without needing Google review)${COLOR_RESET}"
echo -e "     • App name: ${COLOR_BOLD}Mathlore Forge${COLOR_RESET}"
echo -e "     • User support email: ${COLOR_BOLD}${ALLOWED_ADMIN_EMAIL}${COLOR_RESET}"
echo -e "     • Developer contact email: ${COLOR_BOLD}${ALLOWED_ADMIN_EMAIL}${COLOR_RESET}"
echo -e "     • Scopes: Leave defaults (click 'Save and Continue')"
echo -e "     • Test users: Click '+ ADD USERS' and add ${COLOR_BOLD}${ALLOWED_ADMIN_EMAIL}${COLOR_RESET}"
echo -e "  3. Go to 'Credentials' -> Click '+ CREATE CREDENTIALS' -> 'OAuth client ID':"
echo -e "     • Application type: ${COLOR_BOLD}Web application${COLOR_RESET}"
echo -e "     • Name: ${COLOR_BOLD}Mathlore Forge Web${COLOR_RESET}"
echo -e "     • Authorized JavaScript origins: ${COLOR_GREEN}http://localhost:8080${COLOR_RESET} and ${COLOR_GREEN}http://127.0.0.1:8080${COLOR_RESET}"
echo -e "     • Authorized redirect URIs: ${COLOR_GREEN}http://localhost:8080/auth/callback${COLOR_RESET} and ${COLOR_GREEN}http://127.0.0.1:8080/auth/callback${COLOR_RESET}"
echo -e "       ${COLOR_DIM}(Your production Cloud Run URL will be added automatically in Step 10)${COLOR_RESET}"

prompt_var "GOOGLE_CLIENT_ID" "Google OAuth Client ID (ends with .apps.googleusercontent.com)" "${GOOGLE_CLIENT_ID:-}"
prompt_var "GOOGLE_CLIENT_SECRET" "Google OAuth Client Secret" "${GOOGLE_CLIENT_SECRET:-}" true
save_config

# ------------------------------------------------------------------------------
# STEP 4: GitHub Personal Access Token (PAT)
# ------------------------------------------------------------------------------
print_step "4" "GitHub Personal Access Token (PAT)"
echo -e "  Mathlore Forge agents interact with GitHub on your behalf: creating"
echo -e "  branches, committing .mlg files, opening PRs, and squash-merging."
echo ""
echo -e "  ${COLOR_BOLD}To generate a Fine-Grained Token:${COLOR_RESET}"
echo -e "  1. Open: ${COLOR_CYAN}https://github.com/settings/tokens?type=beta${COLOR_RESET}"
echo -e "  2. Resource owner: Select 'mathlingua' (or personal account)"
echo -e "  3. Repository access: Select 'mathlingua/mathlore' and 'mathlingua/mathlore-forge'"
echo -e "  4. Repository permissions:"
echo -e "     • Contents: Read and write"
echo -e "     • Pull requests: Read and write"
echo -e "     • Issues: Read and write"

prompt_var "GITHUB_TOKEN" "GitHub Personal Access Token (github_pat_... or ghp_...)" "${GITHUB_TOKEN:-}" true
save_config

# ------------------------------------------------------------------------------
# STEP 5: Gemini API Key & Secrets Setup
# ------------------------------------------------------------------------------
print_step "5" "Gemini API Key & Generated Secrets"
echo -e "  Gemini 3.8 and Google Antigravity power mathematical reasoning, syntax"
echo -e "  validation, proof construction, and self-improvement flywheels."

prompt_var "GEMINI_API_KEY" "Gemini API Key" "${GEMINI_API_KEY:-}" true

# Generate Webhook Secret if not set
if [ -z "${GITHUB_WEBHOOK_SECRET:-}" ]; then
    GITHUB_WEBHOOK_SECRET=$(openssl rand -hex 20)
    print_info "Generated new GitHub Webhook Secret (HMAC SHA-256): ${GITHUB_WEBHOOK_SECRET}"
fi

# Generate Session Secret Key if not set
if [ -z "${SESSION_SECRET_KEY:-}" ]; then
    SESSION_SECRET_KEY=$(openssl rand -hex 32)
    print_info "Generated new Cookie Session Secret Key."
fi
save_config

# ------------------------------------------------------------------------------
# STEP 6: Enable GCP APIs & Prepare Artifact Registry
# ------------------------------------------------------------------------------
print_step "6" "Enable Cloud APIs & Artifact Registry"
print_info "Enabling required GCP services..."

REQUIRED_APIS=(
    "run.googleapis.com"
    "artifactregistry.googleapis.com"
    "cloudbuild.googleapis.com"
    "secretmanager.googleapis.com"
    "logging.googleapis.com"
    "cloudtrace.googleapis.com"
)
confirm_run "gcloud services enable ${REQUIRED_APIS[*]}"

# Check Artifact Registry
print_info "Checking Docker repository in Artifact Registry..."
if gcloud artifacts repositories describe mathlore-forge --location="$GCP_REGION" >/dev/null 2>&1; then
    print_success "Artifact Registry repository 'mathlore-forge' already exists in ${GCP_REGION}."
else
    print_info "Creating Artifact Registry repository 'mathlore-forge'..."
    confirm_run "gcloud artifacts repositories create mathlore-forge --repository-format=docker --location='${GCP_REGION}' --description='Docker repository for Mathlore Forge'"
fi

# ------------------------------------------------------------------------------
# STEP 7: Build & Push Container Image
# ------------------------------------------------------------------------------
print_step "7" "Build & Push Container Image to Artifact Registry"

# Use git short SHA or latest
GIT_SHORT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
prompt_var "IMAGE_TAG" "Container Image Tag" "${IMAGE_TAG:-$GIT_SHORT_SHA}"
save_config

IMAGE_URI="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/mathlore-forge/app:${IMAGE_TAG}"
print_info "Target container image: ${IMAGE_URI}"

# Check if image exists
IMAGE_EXISTS=$(gcloud artifacts docker images list "${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/mathlore-forge/app" --filter="tags:${IMAGE_TAG}" --format="value(TAGS)" 2>/dev/null || true)

REBUILD="true"
if [ -n "$IMAGE_EXISTS" ]; then
    print_success "Image ${IMAGE_URI} already exists in Artifact Registry."
    read -r -p "$(echo -e "  ${COLOR_BOLD}Rebuild and push a new image anyway? [y/N]: ${COLOR_RESET}")" rebuild_choice
    case "$rebuild_choice" in
        [Yy]) REBUILD="true" ;;
        *) REBUILD="false" ;;
    esac
fi

if [ "$REBUILD" = "true" ]; then
    print_info "Building container image using Google Cloud Build..."
    confirm_run "gcloud builds submit --tag '${IMAGE_URI}' -f infra/Dockerfile ."
fi

# ------------------------------------------------------------------------------
# STEP 8: Populate Secrets in Secret Manager
# ------------------------------------------------------------------------------
print_step "8" "Provision Secret Manager Slots & Payloads"
echo -e "  Cloud Run mounts secrets directly from Secret Manager at runtime."
echo -e "  This guarantees credentials are never baked into container images or Git."

declare -A SECRETS_MAP=(
    ["GEMINI_API_KEY"]="${GEMINI_API_KEY}"
    ["GITHUB_TOKEN"]="${GITHUB_TOKEN}"
    ["GITHUB_WEBHOOK_SECRET"]="${GITHUB_WEBHOOK_SECRET}"
    ["GOOGLE_CLIENT_ID"]="${GOOGLE_CLIENT_ID}"
    ["GOOGLE_CLIENT_SECRET"]="${GOOGLE_CLIENT_SECRET}"
    ["SESSION_SECRET_KEY"]="${SESSION_SECRET_KEY}"
)

for sec_name in "${!SECRETS_MAP[@]}"; do
    sec_val="${SECRETS_MAP[$sec_name]}"

    # 1. Ensure Secret Slot Exists
    if ! gcloud secrets describe "$sec_name" >/dev/null 2>&1; then
        print_info "Creating secret slot '${sec_name}'..."
        confirm_run "gcloud secrets create '${sec_name}' --replication-policy=automatic"
    else
        print_success "Secret slot '${sec_name}' exists."
    fi

    # 2. Check if Version Exists
    HAS_VER=$(gcloud secrets versions list "$sec_name" --filter="state:ENABLED" --format="value(name)" 2>/dev/null | head -n 1 || true)
    UPDATE_VER="false"

    if [ -z "$HAS_VER" ]; then
        UPDATE_VER="true"
    else
        # Prompt if user wants to update existing
        read -r -p "$(echo -e "  Secret ${COLOR_CYAN}${sec_name}${COLOR_RESET} already has a version. Update with current value? [y/N]: ")" upd_choice
        case "$upd_choice" in
            [Yy]) UPDATE_VER="true" ;;
            *) UPDATE_VER="false" ;;
        esac
    fi

    if [ "$UPDATE_VER" = "true" ] && [ -n "$sec_val" ]; then
        real_cmd="echo -n '${sec_val}' | gcloud secrets versions add '${sec_name}' --data-file=-"
        disp_cmd="echo -n '********' | gcloud secrets versions add '${sec_name}' --data-file=-"
        confirm_run "$real_cmd" "$disp_cmd"
    fi
done

# ------------------------------------------------------------------------------
# STEP 9: Provision Infrastructure with Terraform
# ------------------------------------------------------------------------------
print_step "9" "Provision Infrastructure with Terraform"
print_info "Preparing Terraform workspace in infra/terraform/..."

TF_DIR="${SCRIPT_DIR}/infra/terraform"

# Generate terraform.tfvars
TFVARS_FILE="${TF_DIR}/terraform.tfvars"
cat <<EOF > "$TFVARS_FILE"
project_id            = "${GCP_PROJECT_ID}"
region                = "${GCP_REGION}"
image_tag             = "${IMAGE_TAG}"
worker_timeout        = "${WORKER_TIMEOUT:-600s}"
allowed_admin_email   = "${ALLOWED_ADMIN_EMAIL}"
allowed_github_author = "${ALLOWED_GITHUB_AUTHOR}"
EOF
chmod 600 "$TFVARS_FILE"
print_success "Generated ${TFVARS_FILE}."

# Terraform / OpenTofu Init
if [ ! -d "${TF_DIR}/.terraform" ]; then
    print_info "Initializing ${TF_CMD}..."
    confirm_run "cd '${TF_DIR}' && ${TF_CMD} init"
else
    print_success "${TF_CMD} is already initialized."
    read -r -p "$(echo -e "  ${COLOR_BOLD}Run '${TF_CMD} init' again to check for updates? [y/N]: ${COLOR_RESET}")" tf_init_choice
    if [[ "$tf_init_choice" =~ ^[Yy]$ ]]; then
        confirm_run "cd '${TF_DIR}' && ${TF_CMD} init"
    fi
fi

# Terraform / OpenTofu Plan
print_info "Previewing ${TF_CMD} infrastructure execution plan..."
confirm_run "cd '${TF_DIR}' && ${TF_CMD} plan"

# Terraform / OpenTofu Apply
print_info "Applying infrastructure changes to Google Cloud..."
confirm_run "cd '${TF_DIR}' && ${TF_CMD} apply -auto-approve"

# Retrieve Outputs
DASHBOARD_URL=$(cd "${TF_DIR}" && ${TF_CMD} output -raw dashboard_url 2>/dev/null || true)
WEBHOOK_URL=$(cd "${TF_DIR}" && ${TF_CMD} output -raw webhook_url 2>/dev/null || true)
SERVICE_ACCOUNT=$(cd "${TF_DIR}" && ${TF_CMD} output -raw service_account_email 2>/dev/null || true)

if [ -z "$DASHBOARD_URL" ]; then
    DASHBOARD_URL=$(gcloud run services describe mathlore-forge-web --region "${GCP_REGION}" --format="value(status.url)" 2>/dev/null || true)
    WEBHOOK_URL="${DASHBOARD_URL}/webhooks/github"
fi

print_success "Cloud Run Web Service: ${DASHBOARD_URL}"
print_success "GitHub Webhook Target: ${WEBHOOK_URL}"

# ------------------------------------------------------------------------------
# STEP 10: OAuth & GitHub Webhook Configuration
# ------------------------------------------------------------------------------
print_step "10" "Connect Google OAuth & GitHub Webhooks"

echo -e "  ${COLOR_BOLD}A. Add Production Domain to Google OAuth:${COLOR_RESET}"
echo -e "  Now that Cloud Run is deployed, add your live domain to Google OAuth 2.0:"
echo -e "  1. Open: ${COLOR_CYAN}https://console.cloud.google.com/apis/credentials?project=${GCP_PROJECT_ID}${COLOR_RESET}"
echo -e "  2. Click on your OAuth Client ID (${COLOR_BOLD}Mathlore Forge Web${COLOR_RESET})."
echo -e "  3. Under ${COLOR_BOLD}Authorized JavaScript origins${COLOR_RESET}, click ${COLOR_BOLD}+ ADD URI${COLOR_RESET} and add:"
echo -e "     ${COLOR_GREEN}${DASHBOARD_URL}${COLOR_RESET}"
echo -e "  4. Under ${COLOR_BOLD}Authorized redirect URIs${COLOR_RESET}, click ${COLOR_BOLD}+ ADD URI${COLOR_RESET} and add:"
echo -e "     ${COLOR_GREEN}${DASHBOARD_URL}/auth/callback${COLOR_RESET}"
echo -e "  5. Click ${COLOR_BOLD}SAVE${COLOR_RESET}."
echo ""
read -r -p "$(echo -e "  ${COLOR_YELLOW}Press [Enter] once you have updated the Google Cloud Console: ${COLOR_RESET}")"

echo ""
echo -e "  ${COLOR_BOLD}B. Configure the GitHub Webhook in mathlingua/mathlore:${COLOR_RESET}"
echo -e "  1. Open: ${COLOR_CYAN}https://github.com/mathlingua/mathlore/settings/hooks${COLOR_RESET}"
echo -e "  2. Click ${COLOR_BOLD}Add webhook${COLOR_RESET} (or edit existing)."
echo -e "  3. Configure fields:"
echo -e "     • Payload URL:    ${COLOR_GREEN}${WEBHOOK_URL}${COLOR_RESET}"
echo -e "     • Content type:   ${COLOR_BOLD}application/json${COLOR_RESET}"
echo -e "     • Secret:         ${COLOR_GREEN}${GITHUB_WEBHOOK_SECRET}${COLOR_RESET}"
echo -e "     • SSL verify:     ${COLOR_BOLD}Enable SSL verification${COLOR_RESET}"
echo -e "     • Events:         Select ${COLOR_BOLD}Issues${COLOR_RESET}, ${COLOR_BOLD}Pull requests${COLOR_RESET}, ${COLOR_BOLD}Pull request reviews${COLOR_RESET}, ${COLOR_BOLD}Issue comments${COLOR_RESET}"
echo -e "  4. Click ${COLOR_BOLD}Add webhook${COLOR_RESET}."
echo ""
read -r -p "$(echo -e "  ${COLOR_YELLOW}Press [Enter] once you have configured the GitHub Webhook: ${COLOR_RESET}")"

# ------------------------------------------------------------------------------
# STEP 11: Live Service Verification
# ------------------------------------------------------------------------------
print_step "11" "Live Service Verification"
print_info "Testing Cloud Run health endpoint (${DASHBOARD_URL}/healthz)..."

confirm_run "curl -s -i '${DASHBOARD_URL}/healthz'"

echo ""
echo -e "${COLOR_BOLD}${COLOR_GREEN}╔══════════════════════════════════════════════════════════════════════╗${COLOR_RESET}"
echo -e "${COLOR_BOLD}${COLOR_GREEN}║             🎉 MATHLORE FORGE IS DEPLOYED AND LIVE!                ║${COLOR_RESET}"
echo -e "${COLOR_BOLD}${COLOR_GREEN}╚══════════════════════════════════════════════════════════════════════╝${COLOR_RESET}"
echo ""
echo -e "  ${COLOR_BOLD}Web Dashboard:${COLOR_RESET}  ${COLOR_CYAN}${DASHBOARD_URL}${COLOR_RESET}"
echo -e "  ${COLOR_BOLD}Webhook URL:${COLOR_RESET}    ${COLOR_CYAN}${WEBHOOK_URL}${COLOR_RESET}"
echo -e "  ${COLOR_BOLD}Admin Email:${COLOR_RESET}    ${COLOR_CYAN}${ALLOWED_ADMIN_EMAIL}${COLOR_RESET}"
echo -e "  ${COLOR_BOLD}GitHub Author:${COLOR_RESET}  ${COLOR_CYAN}${ALLOWED_GITHUB_AUTHOR}${COLOR_RESET}"
echo -e "  ${COLOR_BOLD}Service Account:${COLOR_RESET}${COLOR_CYAN}${SERVICE_ACCOUNT:-mathlore-forge-sa@${GCP_PROJECT_ID}.iam.gserviceaccount.com}${COLOR_RESET}"
echo ""
echo -e "  ${COLOR_BOLD}Next Steps:${COLOR_RESET}"
echo -e "  1. Open ${COLOR_CYAN}${DASHBOARD_URL}${COLOR_RESET} in your browser and sign in with Google."
echo -e "  2. Test authoring by opening a GitHub issue on ${COLOR_CYAN}mathlingua/mathlore${COLOR_RESET}:"
echo -e "     • Direct item: ${COLOR_BOLD}[Forge] Add monotonicity of set intersection${COLOR_RESET}"
echo -e "     • Abstract proposal: ${COLOR_BOLD}[Forge] Add more number theory content${COLOR_RESET}"
echo ""
echo -e "  ${COLOR_DIM}Configuration saved to .deploy_config. You can safely re-run ./deploy.sh anytime.${COLOR_RESET}"
echo ""
