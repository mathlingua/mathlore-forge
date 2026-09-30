#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Mathlore Forge Teardown and Cleanup Script
# This script stops all running services and deletes GCP resources.
# ==============================================================================

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo '')}"
REGION="${GCP_REGION:-us-central1}"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: GCP_PROJECT_ID is not set and could not be determined from gcloud."
    echo "Please run: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

echo "=================================================="
echo "⚠️  TEARING DOWN MATHLORE FORGE ON GCP"
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "=================================================="
read -p "Are you sure you want to stop and delete all Forge cloud resources? (y/N): " -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# 1. Delete Cloud Run Service (Web Dashboard & Webhook Receiver)
echo "🗑 Deleting Cloud Run service: mathlore-forge-web..."
gcloud run services delete mathlore-forge-web \
    --region "$REGION" \
    --quiet || echo "Service mathlore-forge-web already deleted or not found."

# 2. Delete Cloud Run Job (Agent Worker)
echo "🗑 Deleting Cloud Run Job: mathlore-forge-worker..."
gcloud run jobs delete mathlore-forge-worker \
    --region "$REGION" \
    --quiet || echo "Job mathlore-forge-worker already deleted or not found."

# 3. Delete Artifact Registry Repository (Docker Images)
echo "🗑 Deleting Artifact Registry repository: mathlore-forge..."
gcloud artifacts repositories delete mathlore-forge \
    --location "$REGION" \
    --quiet || echo "Artifact repository mathlore-forge already deleted or not found."

# 4. Optional: Delete Secrets from Secret Manager
read -p "Do you also want to delete the secrets in Secret Manager? (y/N): " -r DELETE_SECRETS
if [[ "$DELETE_SECRETS" =~ ^[Yy]$ ]]; then
    echo "🗑 Deleting secrets from Secret Manager..."
    for SECRET in GEMINI_API_KEY GITHUB_TOKEN GITHUB_WEBHOOK_SECRET GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET SESSION_SECRET_KEY; do
        gcloud secrets delete "$SECRET" --quiet || echo "Secret $SECRET not found."
    done
fi

echo "=================================================="
echo "✔ Teardown complete. All running instances and services have been deleted."
echo "Remember to delete or disable the webhook in GitHub Settings -> Webhooks."
echo "=================================================="
