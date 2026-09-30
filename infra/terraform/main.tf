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

# Artifact Registry for container images
resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = "mathlore-forge"
  description   = "Docker repository for Mathlore Forge"
  format        = "DOCKER"
}

# Cloud Run Service (Web Dashboard & Webhook Receiver)
resource "google_cloud_run_v2_service" "web_service" {
  name     = "mathlore-forge-web"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/mathlore-forge/app:latest"

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "ALLOWED_ADMIN_EMAIL"
        value = "DominicKramer@gmail.com"
      }
      env {
        name  = "ALLOWED_GITHUB_AUTHOR"
        value = "DominicKramer"
      }
    }
  }
}

# Allow unauthenticated traffic to Webhook & Dashboard (auth handled in-app via Google OAuth)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.web_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Cloud Run Job (Long-Running Agent Worker, up to 24h)
resource "google_cloud_run_v2_job" "worker_job" {
  name     = "mathlore-forge-worker"
  location = var.region

  template {
    task_count = 1

    template {
      max_retries = 1
      timeout     = "86400s" # 24 hours

      containers {
        image   = "${var.region}-docker.pkg.dev/${var.project_id}/mathlore-forge/app:latest"
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
          value = "DominicKramer@gmail.com"
        }
        env {
          name  = "ALLOWED_GITHUB_AUTHOR"
          value = "DominicKramer"
        }
      }
    }
  }
}
