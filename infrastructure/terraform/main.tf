terraform {
  required_version = ">= 1.0"

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

# Enable required APIs
resource "google_project_service" "cloud_run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_build" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifact_registry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_trace" {
  service            = "cloudtrace.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_logging" {
  service            = "logging.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "storage_api" {
  service            = "storage-api.googleapis.com"
  disable_on_destroy = false
}

# Artifact Registry repository for service images
resource "google_artifact_registry_repository" "services" {
  location      = var.region
  repository_id = "services"
  description   = "Container images for microservices"
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry]
}

# Artifact Registry repository for base images
resource "google_artifact_registry_repository" "base_images" {
  location      = var.region
  repository_id = "base-images"
  description   = "Base Docker images for microservices"
  format        = "DOCKER"

  depends_on = [google_project_service.artifact_registry]
}

# Cloud Storage bucket for Cloud Build sources
resource "google_storage_bucket" "cloudbuild" {
  name          = "${var.project_id}-cloudbuild-v2"
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.storage_api]
}

# Cloud Storage bucket for execution artifacts (screenshots, files, etc.)
resource "google_storage_bucket" "artifacts" {
  name          = "${var.project_id}-execution-artifacts"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 90
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.storage_api]
}

# Service account for Cloud Run services
resource "google_service_account" "cloud_run_sa" {
  account_id   = "cloud-run-services"
  display_name = "Cloud Run Services"
  description  = "Service account for Cloud Run microservices"
}

# Grant service account access to Artifact Registry
resource "google_artifact_registry_repository_iam_member" "cloud_run_reader" {
  location   = google_artifact_registry_repository.services.location
  repository = google_artifact_registry_repository.services.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Grant service account access to Cloud Storage
resource "google_storage_bucket_iam_member" "cloud_run_storage" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Grant service account access to Cloud Trace
resource "google_project_iam_member" "cloud_run_trace" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Grant service account access to Cloud Logging
resource "google_project_iam_member" "cloud_run_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Output important values
output "artifact_registry_url" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/services"
  description = "Artifact Registry URL for service images"
}

output "base_images_registry_url" {
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/base-images"
  description = "Artifact Registry URL for base images"
}

output "cloudbuild_bucket" {
  value       = google_storage_bucket.cloudbuild.name
  description = "Cloud Storage bucket for Cloud Build sources"
}

output "artifacts_bucket" {
  value       = google_storage_bucket.artifacts.name
  description = "Cloud Storage bucket for execution artifacts"
}

output "service_account_email" {
  value       = google_service_account.cloud_run_sa.email
  description = "Service account email for Cloud Run services"
}
