output "dashboard_url" {
  description = "The public URL of the Mathlore Forge Web Dashboard."
  value       = google_cloud_run_v2_service.web_service.uri
}

output "webhook_url" {
  description = "The GitHub Webhook Payload URL to configure in GitHub repository settings."
  value       = "${google_cloud_run_v2_service.web_service.uri}/webhooks/github"
}

output "artifact_registry_repository" {
  description = "The Artifact Registry Docker repository for container images."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.name}"
}

output "service_account_email" {
  description = "The dedicated IAM Service Account used by Cloud Run."
  value       = google_service_account.forge_sa.email
}
