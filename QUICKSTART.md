# Quick Start Guide

Get your microservices playground up and running in minutes!

## Prerequisites

- ✅ GCP account with billing enabled
- ✅ `gcloud` CLI installed and authenticated
- ✅ Python 3.11+ installed
- ✅ Terraform installed

## Step 1: Verify Configuration

Your project is already configured:

```json
{
  "project_id": "globalwinner",
  "region": "us-east1"
}
```

Verify gcloud is set up:

```bash
gcloud config get-value project
# Should output: globalwinner
```

## Step 2: Deploy Infrastructure

```bash
cd infrastructure/terraform
terraform init
terraform apply
```

Type `yes` when prompted.

This creates:
- Artifact Registry repositories
- Cloud Storage buckets
- Service account with IAM roles
- Enables required APIs

**Time**: ~2-3 minutes
**Cost**: ~$1-2/month

## Step 3: Build Base Images

**On Windows (PowerShell):**
```powershell
cd ..\..\base-images
.\build-all.ps1
```

**On Linux/Mac:**
```bash
cd ../../base-images
chmod +x build-all.sh
./build-all.sh
```

This builds:
- Python base image (~200MB)
- Node.js base image (~150MB)
- Go base image (~40MB)

**Time**: ~10-15 minutes (one-time)
**Cost**: ~$0.04/month storage

## Step 4: Install Development Dependencies

```bash
cd ..
pip install -r requirements.txt
```

## Step 5: Test Deployment CLI

```bash
python -m deploy.cli info
```

You should see:
```
Configuration
Project ID: globalwinner
Region: us-east1
Artifact Registry: services
```

## Step 6: Create Your First Service (Coming Soon)

The service creation tools are next to be built. For now, you have:

✅ Complete deployment system
✅ GCP infrastructure
✅ Base images for fast builds
✅ SDK for writing services

## Available Commands

### Deployment Info

```bash
# Show configuration
python -m deploy.cli info

# List Cloud Run services
python -m deploy.cli services

# List container images
python -m deploy.cli images

# Show deployment status
python -m deploy.cli status
```

### When Services Are Ready

```bash
# Deploy a service
python -m deploy.cli deploy my-service

# Deploy multiple services in parallel
python -m deploy.cli deploy-all service1 service2 service3

# Deploy to staging
python -m deploy.cli deploy my-service --env staging

# Rollback to previous version
python -m deploy.cli rollback my-service a7b3c9d2

# List deployments
python -m deploy.cli list
```

## Writing a Microservice

Example service structure:

```python
# services/my-service/src/handler.py

from playground_sdk import handler, RunContext, router, get_logger

logger = get_logger(__name__)

@handler
async def create_order(run: RunContext, amount: float, user_id: int):
    """Create an order - automatically tracked with run.run_id"""

    logger.info(f"Creating order in run: {run.run_id}")

    # Call other services
    result = await router.call_service('db-service', '''
        mutation {
            insert(table: "orders", data: {amount: $amount, user_id: $user_id}) {
                id
            }
        }
    ''', {'amount': amount, 'user_id': user_id})

    return result
```

## Next Steps

1. ✅ Infrastructure deployed
2. ✅ Base images built
3. 🔲 Build API Gateway
4. 🔲 Create service templates
5. 🔲 Build example services (db-service, storage-service)
6. 🔲 Create CLI for `playground create/dev`

## Troubleshooting

### Permission Denied

```bash
# On Windows, make sure you're in PowerShell (not CMD)
# On Linux/Mac, make scripts executable:
chmod +x base-images/build-all.sh
```

### Terraform Errors

```bash
# Make sure you're authenticated:
gcloud auth application-default login

# Verify project:
gcloud config get-value project
```

### Build Errors

```bash
# Check if APIs are enabled:
gcloud services list --enabled

# Should include:
# - run.googleapis.com
# - cloudbuild.googleapis.com
# - artifactregistry.googleapis.com
```

## Cost Monitoring

Check your costs:

```bash
# View current month costs
gcloud billing accounts list
gcloud alpha billing budgets list
```

Set up budget alerts in GCP Console:
- Budget: $20/month
- Alert at: 50%, 90%, 100%

## Clean Up (If Needed)

To remove everything:

```bash
# Delete infrastructure
cd infrastructure/terraform
terraform destroy

# Delete images (optional)
gcloud artifacts repositories delete services --location=us-east1
gcloud artifacts repositories delete base-images --location=us-east1
```

## Getting Help

- **Logs**: Check Cloud Logging in GCP Console
- **Builds**: Check Cloud Build history
- **Services**: Check Cloud Run console

## What You Can Do Now

1. ✅ Deploy infrastructure with Terraform
2. ✅ Build base images for fast deployments
3. ✅ Use deployment CLI to manage services (once created)
4. ✅ Write microservices using playground_sdk

## What's Coming Next

- API Gateway for routing requests
- Service templates for quick creation
- DB service (SQLite + Cloud Storage)
- Storage service (Cloud Storage wrapper)
- CLI for `playground create/dev/deploy`
- Complete documentation

Ready to continue building? Check PROGRESS.md for detailed status!
