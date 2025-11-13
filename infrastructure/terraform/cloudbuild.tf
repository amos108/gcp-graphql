# Cloud Build configuration and permissions

# Get Cloud Build service account
data "google_project" "project" {
  project_id = var.project_id
}

locals {
  cloudbuild_sa = "${data.google_project.project.number}@cloudbuild.gserviceaccount.com"
}

# Grant Cloud Build access to Artifact Registry
resource "google_artifact_registry_repository_iam_member" "cloudbuild_services" {
  location   = google_artifact_registry_repository.services.location
  repository = google_artifact_registry_repository.services.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${local.cloudbuild_sa}"
}

resource "google_artifact_registry_repository_iam_member" "cloudbuild_base_images" {
  location   = google_artifact_registry_repository.base_images.location
  repository = google_artifact_registry_repository.base_images.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${local.cloudbuild_sa}"
}

# Grant Cloud Build access to Cloud Run (for deployments)
resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${local.cloudbuild_sa}"
}

# Grant Cloud Build ability to act as Cloud Run service account
resource "google_service_account_iam_member" "cloudbuild_sa_user" {
  service_account_id = google_service_account.cloud_run_sa.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${local.cloudbuild_sa}"
}

# Grant Cloud Build access to Cloud Storage
resource "google_storage_bucket_iam_member" "cloudbuild_storage" {
  bucket = google_storage_bucket.cloudbuild.name
  role   = "roles/storage.admin"
  member = "serviceAccount:${local.cloudbuild_sa}"
}

# Output Cloud Build service account
output "cloudbuild_service_account" {
  value       = local.cloudbuild_sa
  description = "Cloud Build service account email"
}
