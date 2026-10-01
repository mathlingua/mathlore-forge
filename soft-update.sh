#!/usr/bin/env bash
set -euo pipefail

echo "Building container image via Cloud Build..."
gcloud builds submit --tag 'us-central1-docker.pkg.dev/mathlore-forge/mathlore-forge/app:latest' .

echo "Deploying to Cloud Run with 4Gi memory, 2 CPUs, persistent GCS sync, and always-allocated CPU..."
gcloud run deploy mathlore-forge-web \
  --image 'us-central1-docker.pkg.dev/mathlore-forge/mathlore-forge/app:latest' \
  --region us-central1 \
  --project mathlore-forge \
  --memory 4Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 1 \
  --no-cpu-throttling \
  --set-env-vars "GCS_DATA_BUCKET=mathlore-forge-data-storage"
