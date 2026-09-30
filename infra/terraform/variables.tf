variable "project_id" {
  description = "The GCP Project ID where resources will be provisioned."
  type        = string
}

variable "region" {
  description = "The GCP region for all regional resources (Cloud Run, Artifact Registry)."
  type        = string
  default     = "us-central1"
}

variable "image_tag" {
  description = "The Docker container image tag to deploy (defaults to 'latest' or a git commit SHA)."
  type        = string
  default     = "latest"
}

variable "allowed_admin_email" {
  description = "The only email authorized to access the Mathlore Forge dashboard."
  type        = string
  default     = "DominicKramer@gmail.com"
}

variable "allowed_github_author" {
  description = "The GitHub username authorized to trigger autonomous authoring flows."
  type        = string
  default     = "DominicKramer"
}
