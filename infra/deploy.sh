#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Mathlore Forge GCP Cloud Run & Cloud Run Jobs Deployment Script
# ==============================================================================

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo '')}"
REGION="${GCP_REGION:-us-central1}"
IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/mathlore-forge/app:latest"

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: GCP_PROJECT_ID is not set and could not be determined from gcloud."
    echo "Please run: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

echo "=================================================="
echo "🚀 Deploying Mathlore Forge to GCP"
echo "Project:  $PROJECT_ID"
echo "Region:   $REGION"
echo "Image:    $IMAGE_NAME"
echo "=================================================="

# 1. Ensure Artifact Registry repository exists
echo "📦 Ensuring Artifact Registry repository exists..."
gcloud artifacts repositories describe mathlore-forge --location="$REGION" &>/dev/null || \
    gcloud artifacts repositories create mathlore-forge \
        --repository-format=docker \
        --location="$REGION" \
        --description="Docker repository for Mathlore Forge"

# 2. Build and push container image using Cloud Build
echo "🏗 Building and pushing container image..."
gcloud builds submit --tag "$IMAGE_NAME" -f infra/Dockerfile .

# 3. Deploy Webhook & Dashboard to Cloud Run Service
echo "🌐 Deploying Webhook & Dashboard to Cloud Run Service..."
gcloud run deploy mathlore-forge-web \
    --image "$IMAGE_NAME" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --set-env-vars "ALLOWED_ADMIN_EMAIL=DominicKramer@gmail.com,ALLOWED_GITHUB_AUTHOR=DominicKramer" \
    --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest,GITHUB_WEBHOOK_SECRET=GITHUB_WEBHOOK_SECRET:latest,GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID:latest,GOOGLE_CLIENT_SECRET=GOOGLE_CLIENT_SECRET:latest,SESSION_SECRET_KEY=SESSION_SECRET_KEY:latest" \
    --min-instances 0 \
    --max-instances 5 \
    --memory 1Gi \
    --cpu 1

# 4. Deploy Long-Running Agent Worker to Cloud Run Jobs
echo "⚙ Deploying Agent Worker to Cloud Run Jobs..."
gcloud run jobs deploy mathlore-forge-worker \
    --image "$IMAGE_NAME" \
    --region "$REGION" \
    --command "mathlore-forge" \
    --args "worker" \
    --set-env-vars "ALLOWED_ADMIN_EMAIL=DominicKramer@gmail.com,ALLOWED_GITHUB_AUTHOR=DominicKramer" \
    --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest" \
    --max-retries 1 \
    --task-timeout 24h \
    --memory 4Gi \
    --cpu 2

WEB_URL=$(gcloud run services describe mathlore-forge-web --region="$REGION" --format='value(status.url)')
echo "=================================================="
echo "✔ Deployment Successful!"
echo "Dashboard & Webhook URL: $WEB_URL"
echo "GitHub Webhook Target:   $WEB_URL/webhooks/github"
echo "=================================================="
