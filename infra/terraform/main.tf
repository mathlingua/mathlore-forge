terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ==============================================================================
# 1. Enable Required GCP APIs
# ==============================================================================
locals {
  services = [
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
  ]
}

resource "google_project_service" "enabled_apis" {
  for_each           = toset(local.services)
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

# ==============================================================================
# 2. Dedicated IAM Service Account
# ==============================================================================
resource "google_service_account" "forge_sa" {
  account_id   = "mathlore-forge-sa"
  display_name = "Mathlore Forge Service Account"
  description  = "Dedicated runtime service account for Mathlore Forge web app and agent workers"
  depends_on   = [google_project_service.enabled_apis]
}

# Grant Secret Manager Access to the Service Account
resource "google_project_iam_member" "secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.forge_sa.email}"
}

# Grant Cloud Logging Writer Access
resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.forge_sa.email}"
}

# Grant Cloud Trace Agent Access
resource "google_project_iam_member" "trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.forge_sa.email}"
}

# Grant Cloud Run Developer Access (allows web service to trigger Cloud Run Jobs)
resource "google_project_iam_member" "run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.forge_sa.email}"
}

# ==============================================================================
# 3. Secret Manager Secrets
# ==============================================================================
locals {
  secret_keys = [
    "GEMINI_API_KEY",
    "GITHUB_TOKEN",
    "GITHUB_WEBHOOK_SECRET",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "SESSION_SECRET_KEY",
  ]
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(local.secret_keys)
  secret_id = each.key

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled_apis]
}

# ==============================================================================
# 4. Artifact Registry Repository
# ==============================================================================
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "mathlore-forge"
  description   = "Docker repository for Mathlore Forge container images"
  format        = "DOCKER"
  depends_on    = [google_project_service.enabled_apis]
}

# ==============================================================================
# 5. Cloud Run Service (Web Dashboard & Webhook Receiver)
# ==============================================================================
resource "google_cloud_run_v2_service" "web_service" {
  name     = "mathlore-forge-web"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.forge_sa.email

    scaling {
      min_instance_count = 1
      max_instance_count = 1
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.name}/app:${var.image_tag}"

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }

      ports {
        container_port = 8080
      }

      # Static environment variables
      env {
        name  = "ALLOWED_ADMIN_EMAIL"
        value = var.allowed_admin_email
      }
      env {
        name  = "ALLOWED_GITHUB_AUTHOR"
        value = var.allowed_github_author
      }
      env {
        name  = "GCS_DATA_BUCKET"
        value = "mathlore-forge-data-storage"
      }

      # Secrets mounted from Secret Manager
      dynamic "env" {
        for_each = local.secret_keys
        content {
          name = env.value
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.secrets[env.value].secret_id
              version = "latest"
            }
          }
        }
      }

      startup_probe {
        http_get {
          path = "/healthz"
          port = 8080
        }
        initial_delay_seconds = 2
        period_seconds        = 5
        failure_threshold     = 3
      }
    }
  }

  depends_on = [
    google_project_service.enabled_apis,
    google_project_iam_member.secret_accessor,
  ]
}

# Allow public unauthenticated access to Webhook & Dashboard (Google OAuth handles user auth)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.web_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ==============================================================================
# 6. Cloud Run Job (Long-Running Agent Worker)
# ==============================================================================
resource "google_cloud_run_v2_job" "worker_job" {
  name     = "mathlore-forge-worker"
  location = var.region

  template {
    task_count = 1

    template {
      service_account = google_service_account.forge_sa.email
      max_retries     = 1
      timeout         = var.worker_timeout # Defaults to 10 minutes (600s)

      containers {
        image   = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.name}/app:${var.image_tag}"
        command = ["mathlore-forge"]
        args    = ["worker"]

        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }

        env {
          name  = "ALLOWED_ADMIN_EMAIL"
          value = var.allowed_admin_email
        }
        env {
          name  = "ALLOWED_GITHUB_AUTHOR"
          value = var.allowed_github_author
        }

        dynamic "env" {
          for_each = local.secret_keys
          content {
            name = env.value
            value_source {
              secret_key_ref {
                secret  = google_secret_manager_secret.secrets[env.value].secret_id
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.enabled_apis,
    google_project_iam_member.secret_accessor,
  ]
}
