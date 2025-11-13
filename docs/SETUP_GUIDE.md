# Complete Setup Guide

Step-by-step guide to deploy your GCP Microservices Playground.

## Prerequisites

- ✅ GCP account with billing enabled
- ✅ `gcloud` CLI installed and authenticated
- ✅ Python 3.11+ installed
- ✅ Terraform installed
- ✅ Git initialized in this repository

## Step 1: Verify GCP Configuration (2 minutes)

```bash
# Check current project
gcloud config get-value project
# Should output: true-ability-399619 

# Check region
gcloud config get-value compute/region
# Should output: us-east1

# If not set correctly:
gcloud config set project true-ability-399619 
gcloud config set compute/region us-east1
```

## Step 2: Install Python Dependencies (5 minutes)

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Step 3: Deploy Infrastructure with Terraform (5-10 minutes)

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Review what will be created
terraform plan

# Deploy infrastructure
terraform apply
```

Type `yes` when prompted.

**What gets created:**
- Artifact Registry repositories (services, base-images)
- Cloud Storage buckets (cloudbuild, execution-artifacts)
- Service account with IAM roles
- API enablement (Cloud Run, Cloud Build, Artifact Registry, etc.)

**Cost**: ~$1-2/month

## Step 4: Build Base Images (10-15 minutes, one-time)

```bash
cd ../../base-images

# Windows (PowerShell):
.\build-all.ps1

# Linux/Mac:
chmod +x build-all.sh
./build-all.sh
```

This builds:
- Python base image (~200MB)
- Node.js base image (~150MB)
- Go base image (~40MB)

**Note**: This is a one-time operation. Future service builds will be fast (5-10 seconds).

## Step 5: Set Up CI/CD (2 minutes)

```bash
cd ..

# Create build triggers
python -m cicd.cli setup

# Verify triggers created
python -m cicd.cli list
```

## Step 6: Deploy API Gateway (3-5 minutes)

```bash
# Deploy the API Gateway
python -m deploy.cli deploy api-gateway

# Wait for deployment to complete
# You'll see: ✅ Successfully deployed api-gateway@xxxxxxxx
```

## Step 7: Verify Deployment (1 minute)

```bash
# List deployed services
python -m deploy.cli services

# Should show:
# - api-gateway with URL

# Check deployment status
python -m deploy.cli status

# Test API Gateway
python -m deploy.cli list
```

## Step 8: Create Your First Service (5 minutes)

```bash
# Create a new service from template
python tools/create_service.py my-first-service \
  --lang python \
  --description "My first microservice"

# Navigate to the service
cd services/my-first-service

# Edit the handlers (optional)
# Edit src/handlers.py to add your logic

# Deploy it!
cd ../..
python -m deploy.cli deploy my-first-service
```

## Step 9: Test End-to-End (2 minutes)

```bash
# Get API Gateway URL
python -m deploy.cli services | grep api-gateway

# Test health endpoint
curl https://api-gateway-xxx.run.app/health

# List discovered services
curl https://api-gateway-xxx.run.app/services

# Should show:
# - api-gateway
# - my-first-service
```

## Troubleshooting

### Permission Errors

```bash
# Ensure you're authenticated
gcloud auth application-default login

# Check active account
gcloud auth list
```

### Terraform Errors

```bash
# If resources already exist:
terraform import <resource> <id>

# Or destroy and recreate:
terraform destroy
terraform apply
```

### Build Failures

```bash
# Check Cloud Build logs
gcloud builds list --limit=10

# View specific build
gcloud builds log <build-id>
```

### Deployment Failures

```bash
# Check if service exists
gcloud run services list --region=us-east1

# View service logs
gcloud run services logs read <service-name> --limit=100
```

## What's Next?

You now have a complete microservices platform! Here's what you can do:

### Create More Services

```bash
# Create payment service
python tools/create_service.py payment-service \
  --lang python \
  --description "Payment processing service"

# Create order service
python tools/create_service.py order-service \
  --lang nodejs \
  --description "Order management service"

# Deploy them
python -m deploy.cli deploy-all payment-service order-service --parallel
```

### Monitor Your Services

```bash
# View all services
python -m deploy.cli services

# View deployment history
python -m deploy.cli list

# View container images
python -m deploy.cli images
```

### Update Services

```bash
# Make changes to your service code
vim services/my-first-service/src/handlers.py

# Commit changes
git add .
git commit -m "Update handlers"

# Deploy (only rebuilds if code changed)
python -m deploy.cli deploy my-first-service
```

### Rollback if Needed

```bash
# List deployed versions
python -m deploy.cli list my-first-service

# Rollback to previous version
python -m deploy.cli rollback my-first-service abc123
```

## Cost Monitoring

Check your costs regularly:

```bash
# View current billing
gcloud beta billing accounts list

# Set up budget alerts in GCP Console:
# 1. Go to Billing > Budgets & alerts
# 2. Create budget: $20/month
# 3. Set alerts at: 50%, 90%, 100%
```

## Next Steps

1. ✅ Infrastructure deployed
2. ✅ API Gateway running
3. ✅ First service created
4. 🔜 Build more services
5. 🔜 Add business logic
6. 🔜 Connect services together
7. 🔜 Add UI frontends

## Summary

You've successfully:
- ✅ Deployed GCP infrastructure
- ✅ Built base Docker images
- ✅ Set up CI/CD pipelines
- ✅ Deployed API Gateway
- ✅ Created and deployed your first microservice
- ✅ Verified end-to-end functionality

**Total setup time**: ~30-40 minutes

**Monthly cost**: ~$2-3 (idle) + usage-based costs

Congratulations! Your microservices platform is ready! 🎉
