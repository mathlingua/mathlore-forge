gcloud builds submit --tag 'us-central1-docker.pkg.dev/mathlore-forge/mathlore-forge/app:latest' .

gcloud run deploy mathlore-forge-web \
  --image 'us-central1-docker.pkg.dev/mathlore-forge/mathlore-forge/app:latest' \
  --region us-central1 \
  --project mathlore-forge

