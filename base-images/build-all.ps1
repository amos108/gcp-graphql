# Build all base images and push to Artifact Registry
# PowerShell version for Windows

$ErrorActionPreference = "Stop"

# Load config
$config = Get-Content "..\config.json" | ConvertFrom-Json
$PROJECT_ID = $config.project_id
$REGION = $config.region

Write-Host "Building base images for project: $PROJECT_ID"
Write-Host "Region: $REGION"

# Build Python base image
Write-Host ""
Write-Host "Building Python base image..."
Set-Location python-playground
gcloud builds submit `
  --tag "$REGION-docker.pkg.dev/$PROJECT_ID/base-images/python-playground:latest" `
  --gcs-source-staging-dir="gs://$PROJECT_ID-cloudbuild-v2/source" `
  --project $PROJECT_ID
Set-Location ..

# Build Node.js base image
Write-Host ""
Write-Host "Building Node.js base image..."
Set-Location nodejs-playground
gcloud builds submit `
  --tag "$REGION-docker.pkg.dev/$PROJECT_ID/base-images/nodejs-playground:latest" `
  --gcs-source-staging-dir="gs://$PROJECT_ID-cloudbuild-v2/source" `
  --project $PROJECT_ID
Set-Location ..

# Build Go base image
Write-Host ""
Write-Host "Building Go base image..."
Set-Location go-playground
gcloud builds submit `
  --tag "$REGION-docker.pkg.dev/$PROJECT_ID/base-images/go-playground:latest" `
  --gcs-source-staging-dir="gs://$PROJECT_ID-cloudbuild-v2/source" `
  --project $PROJECT_ID
Set-Location ..

Write-Host ""
Write-Host "✅ All base images built successfully!"
