# Terraform Infrastructure

This directory contains Terraform configuration for setting up GCP infrastructure.

## What Gets Created

- **Artifact Registry repositories**:
  - `services`: For microservice container images
  - `base-images`: For base Docker images (Python, Node.js, Go)

- **Cloud Storage buckets**:
  - `{project}_cloudbuild`: For Cloud Build source code
  - `{project}-execution-artifacts`: For execution artifacts (screenshots, files, etc.)

- **Service Account**: For Cloud Run services with appropriate permissions

- **API Enablement**: Cloud Run, Cloud Build, Artifact Registry, Cloud Trace, Cloud Logging, Storage API

## Prerequisites

1. Install Terraform: https://www.terraform.io/downloads
2. Authenticate with GCP:
   ```bash
   gcloud auth application-default login
   ```

## Usage

### Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

### Plan Changes

```bash
terraform plan
```

### Apply Infrastructure

```bash
terraform apply
```

Review the plan and type `yes` to confirm.

### Destroy Infrastructure

```bash
terraform destroy
```

**Warning**: This will delete all resources. Use with caution!

## Outputs

After `terraform apply`, you'll see:

- `artifact_registry_url`: URL for pushing service images
- `base_images_registry_url`: URL for pushing base images
- `cloudbuild_bucket`: Bucket name for Cloud Build sources
- `artifacts_bucket`: Bucket name for execution artifacts
- `service_account_email`: Service account email for Cloud Run

## Configuration

Edit `terraform.tfvars` to change:

```hcl
project_id = "your-gcp-project-id"
region     = "us-east1"
```

## Cost Estimate

With default settings, idle costs are approximately:

- Artifact Registry: ~$0.10/GB/month
- Cloud Storage: ~$0.02/GB/month
- **Total idle cost**: ~$1-2/month

No charges for:
- Enabled APIs (free)
- Service accounts (free)
- IAM roles (free)
