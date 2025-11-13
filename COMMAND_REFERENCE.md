# Quick Command Reference

Fast reference for all CLI commands.

## 🚀 Deployment

```bash
# Deploy single service
python -m deploy.cli deploy <service-name>

# Deploy to staging
python -m deploy.cli deploy <service-name> --env staging

# Force rebuild
python -m deploy.cli deploy <service-name> --force

# Deploy multiple services in parallel
python -m deploy.cli deploy-all service1 service2 service3

# Rollback to previous version
python -m deploy.cli rollback <service-name> <git-sha>

# List deployments
python -m deploy.cli list
python -m deploy.cli list <service-name>

# Show deployment status table
python -m deploy.cli status

# List Cloud Run services
python -m deploy.cli services

# List container images
python -m deploy.cli images
python -m deploy.cli images <service-name>

# Show configuration
python -m deploy.cli info
```

## 🔄 CI/CD

```bash
# Set up all build triggers
python -m cicd.cli setup

# List all triggers
python -m cicd.cli list

# Create base image triggers
python -m cicd.cli create-base-images

# Create trigger for specific service
python -m cicd.cli create-service <service-name>

# Run a trigger manually
python -m cicd.cli run <trigger-id>
python -m cicd.cli run <trigger-id> --branch develop

# Delete a trigger
python -m cicd.cli delete <trigger-id>

# Show CI/CD configuration
python -m cicd.cli info
```

## 🛠️ Service Creation

```bash
# Create Python service
python tools/create_service.py <service-name> --lang python

# Create Node.js service
python tools/create_service.py <service-name> --lang nodejs

# With description
python tools/create_service.py payment-service \
  --lang python \
  --description "Payment processing service"

# List available templates
python tools/create_service.py list-templates

# Create in specific directory
python tools/create_service.py my-service --lang python --output /path/to/dir
```

## 🏗️ Infrastructure

```bash
# Initialize Terraform
cd infrastructure/terraform
terraform init

# Preview changes
terraform plan

# Deploy infrastructure
terraform apply

# Destroy infrastructure
terraform destroy

# View outputs
terraform output
```

## 📦 Base Images

```bash
# Build all base images
cd base-images
.\build-all.ps1  # Windows (PowerShell)
./build-all.sh   # Linux/Mac

# Build individual image
cd base-images/python-playground
gcloud builds submit --config cloudbuild.yaml
```

## 🔍 Monitoring & Logs

```bash
# View service logs
gcloud run services logs read <service-name> --limit=100

# Follow logs in real-time
gcloud run services logs tail <service-name>

# Search logs by run_id
gcloud logging read 'jsonPayload.run_id="exec_..."'

# List recent builds
gcloud builds list --limit=10

# View build logs
gcloud builds log <build-id>

# Describe service
gcloud run services describe <service-name> --region=us-east1
```

## 📊 GCP Management

```bash
# List Cloud Run services
gcloud run services list --region=us-east1

# List container images
gcloud artifacts docker images list us-east1-docker.pkg.dev/globalwinner/services

# View current project
gcloud config get-value project

# Set project
gcloud config set project globalwinner

# Set region
gcloud config set compute/region us-east1

# Authenticate
gcloud auth login
gcloud auth application-default login
```

## 🧪 Local Development

```bash
# Run service locally (Python)
cd services/<service-name>
export SERVICE_NAME=<service-name>
export DEBUG=true
python -m src.main

# Run service locally (Node.js)
cd services/<service-name>
export PORT=8080
npm start

# With hot reload
npm run dev
```

## ✅ Health Checks

```bash
# Check service health
curl https://<service-name>-xxx.run.app/health

# Check API Gateway services
curl https://api-gateway-xxx.run.app/services

# Test endpoint
curl -X POST https://api-gateway-xxx.run.app/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "..."}'
```

## 💰 Cost Monitoring

```bash
# List billing accounts
gcloud billing accounts list

# View budget alerts
gcloud beta billing budgets list --billing-account=<account-id>

# View current costs (in Console)
# Billing > Reports
```

## 🔐 Permissions

```bash
# List IAM roles
gcloud projects get-iam-policy globalwinner

# Grant role to service account
gcloud projects add-iam-policy-binding globalwinner \
  --member="serviceAccount:..." \
  --role="roles/..."

# List service accounts
gcloud iam service-accounts list
```

## 📝 Quick Workflows

### Create and Deploy New Service
```bash
# 1. Create from template
python tools/create_service.py my-service --lang python

# 2. Edit code
cd services/my-service
vim src/handlers.py

# 3. Test locally
python -m src.main

# 4. Deploy
cd ../..
python -m deploy.cli deploy my-service

# 5. Verify
python -m deploy.cli services
```

### Update Existing Service
```bash
# 1. Make changes
vim services/my-service/src/handlers.py

# 2. Commit
git add .
git commit -m "Update handlers"

# 3. Deploy (auto-detects changes)
python -m deploy.cli deploy my-service

# 4. Check status
python -m deploy.cli list my-service
```

### Rollback After Bad Deploy
```bash
# 1. List versions
python -m deploy.cli list my-service

# 2. Rollback to previous
python -m deploy.cli rollback my-service <previous-sha>

# 3. Verify
curl https://my-service-xxx.run.app/health
```

### Set Up New Environment
```bash
# 1. Deploy infrastructure
cd infrastructure/terraform
terraform apply

# 2. Build base images
cd ../../base-images
.\build-all.ps1

# 3. Set up CI/CD
python -m cicd.cli setup

# 4. Deploy API Gateway
python -m deploy.cli deploy api-gateway

# Done!
```

---

## 🎯 Most Common Commands

```bash
# Deploy service
python -m deploy.cli deploy <service-name>

# Create service
python tools/create_service.py <service-name> --lang python

# Check status
python -m deploy.cli status

# View logs
gcloud run services logs read <service-name>

# List services
python -m deploy.cli services
```

---

**Keep this handy for quick reference! 📌**
