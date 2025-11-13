# 🎯 Complete Platform Guide

The ultimate guide to your GCP Microservices Playground.

## 📖 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Creating Services](#creating-services)
4. [Deploying Services](#deploying-services)
5. [Service Communication](#service-communication)
6. [Monitoring & Tracing](#monitoring--tracing)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [Reference](#reference)

---

## Overview

### What is This?

A production-ready microservices platform on GCP featuring:

- ⚡ **Ultra-fast builds** (5-10 seconds)
- 💰 **Minimal cost** (~$2-3/month idle)
- 🔍 **Complete tracing** (every operation tracked with run_id)
- 🚀 **Auto-scaling** (scales to zero)
- 🛠️ **Multi-language** (Python, Node.js, Go)
- 🔄 **CI/CD ready** (automated builds)

### Architecture

```
Client → API Gateway → Microservices → Infrastructure
                ↓          ↓              ↓
          run_id tracking across all components
```

---

## Quick Start

### 1. Deploy Everything (30 minutes)

```bash
# Deploy infrastructure
cd infrastructure/terraform && terraform apply

# Build base images
cd ../../base-images && .\build-all.ps1

# Set up CI/CD
python -m cicd.cli setup

# Deploy API Gateway
python -m deploy.cli deploy api-gateway
```

### 2. Create Your First Service (2 minutes)

```bash
python tools/create_service.py my-service --lang python
python -m deploy.cli deploy my-service
```

### 3. Verify It Works

```bash
curl https://api-gateway-xxx.run.app/services
```

---

## Creating Services

### Using Templates

```bash
# Python service
python tools/create_service.py payment-service \
  --lang python \
  --description "Payment processing"

# Node.js service
python tools/create_service.py order-service \
  --lang nodejs \
  --description "Order management"

# Go service (template coming soon)
python tools/create_service.py inventory-service \
  --lang go \
  --description "Inventory tracking"
```

### Service Structure

Every service has the same structure:

```
services/my-service/
├── src/
│   ├── main.py (or index.js)
│   └── handlers.py
├── config.json
├── Dockerfile
├── requirements.txt (or package.json)
└── README.md
```

### Writing a Handler (Python)

```python
# services/my-service/src/handlers.py

from playground_sdk import handler, RunContext, router

@handler
async def create_order(run: RunContext, order_data: dict):
    """Create an order"""

    # Automatically tracked with run.run_id
    logger.info(f"Creating order in run: {run.run_id}")

    # Call other services
    payment_result = await router.call_service('payment-service', '''
        mutation {
            processPayment(amount: $amount) {
                success
                transactionId
            }
        }
    ''', {'amount': order_data['amount']})

    # Call DB service
    db_result = await router.call_service('db-service', '''
        mutation {
            insert(table: "orders", data: $data) {
                id
            }
        }
    ''', {'data': order_data})

    return {
        'orderId': db_result['id'],
        'paymentStatus': payment_result['success'],
        'run_id': run.run_id
    }
```

### Writing a Handler (Node.js)

```javascript
// services/my-service/src/index.js

app.post('/api/create-order', async (req, res) => {
  try {
    const runId = req.runId; // Automatically injected

    // Your business logic
    const result = {
      success: true,
      run_id: runId
    };

    res.json(result);
  } catch (error) {
    console.error({ run_id: req.runId, error: error.message });
    res.status(500).json({ error: error.message });
  }
});
```

---

## Deploying Services

### Deploy Single Service

```bash
# Deploy to production
python -m deploy.cli deploy payment-service

# Deploy to staging
python -m deploy.cli deploy payment-service --env staging

# Force rebuild
python -m deploy.cli deploy payment-service --force
```

### Deploy Multiple Services

```bash
# Deploy in parallel
python -m deploy.cli deploy-all payment-service order-service email-service

# Deploy sequentially
python -m deploy.cli deploy-all service1 service2 --no-parallel
```

### Check Deployment Status

```bash
# List all deployments
python -m deploy.cli list

# Show status table
python -m deploy.cli status

# List running services
python -m deploy.cli services

# List container images
python -m deploy.cli images
```

### Rollback

```bash
# List deployed versions
python -m deploy.cli list payment-service

# Rollback to specific version
python -m deploy.cli rollback payment-service abc123def
```

---

## Service Communication

### Calling Other Services

Services can call each other using the SDK:

```python
from playground_sdk import router

# Call any service
result = await router.call_service(
    service_name='db-service',
    query='''
        mutation {
            insert(table: "users", data: $data) {
                id
            }
        }
    ''',
    variables={'data': user_data}
)
```

### Available Services

```bash
# List all services
curl https://api-gateway-xxx.run.app/services

# Call service directly
curl -X POST https://api-gateway-xxx.run.app/call/payment-service \
  -H "Content-Type: application/json" \
  -d '{"query": "..."}'
```

### Service Discovery

Services are automatically discovered by the API Gateway:

1. Deploy service to Cloud Run
2. API Gateway auto-discovers it
3. Immediately available to other services

No configuration needed!

---

## Monitoring & Tracing

### run_id Tracking

Every request gets a unique `run_id`:

```
exec_20250113_103045_a7b3c9d2
```

This tracks:
- All logs from all services
- Database operations
- File operations
- API calls
- UI interactions (when ui-automation-service deployed)

### Query by run_id

**In Cloud Logging:**
```
run_id="exec_20250113_103045_a7b3c9d2"
```

**In Cloud Trace:**
```
Search for trace ID containing the run_id
```

### View Logs

```bash
# Service logs
gcloud run services logs read payment-service --limit=100

# Follow logs
gcloud run services logs tail payment-service

# Filter by run_id
gcloud logging read 'jsonPayload.run_id="exec_..."'
```

### Metrics & Monitoring

All services automatically send:
- ✅ Request counts
- ✅ Latency metrics
- ✅ Error rates
- ✅ Traces (OpenTelemetry)

View in:
- Cloud Console > Cloud Run > [service] > Metrics
- Cloud Console > Trace > Trace List
- Cloud Console > Logging > Logs Explorer

---

## Best Practices

### 1. Service Design

```python
# ✅ GOOD: Small, focused services
@handler
async def create_order(run: RunContext, data: dict):
    # Single responsibility
    return await process_order(data)

# ❌ BAD: God service doing everything
@handler
async def do_everything(run: RunContext, data: dict):
    create_order()
    process_payment()
    send_email()
    update_inventory()
    # Too much!
```

### 2. Error Handling

```python
# ✅ GOOD: Proper error handling
@handler
async def process_payment(run: RunContext, amount: float):
    try:
        result = await stripe.charge(amount)
        return {"success": True}
    except StripeError as e:
        logger.error(f"Payment failed: {e}", extra={'run_id': run.run_id})
        return {"success": False, "error": str(e)}
```

### 3. Use run_id

```python
# ✅ GOOD: Always log with run_id
logger.info("Processing payment", extra={
    'run_id': run.run_id,
    'amount': amount
})

# ❌ BAD: Logs without context
print("Processing payment")  # Can't trace this!
```

### 4. Configuration

```python
# ✅ GOOD: Use environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')

# ❌ BAD: Hardcoded values
DB_HOST = 'production-db.example.com'
```

### 5. Testing Locally

```bash
# Set up local environment
export LOCAL_SERVICE=payment-service
export PAYMENT_SERVICE_URL=http://localhost:8080
export DB_SERVICE_URL=https://db-service-xxx.run.app

# Run locally
cd services/payment-service
python -m src.main
```

---

## Troubleshooting

### Build Fails

```bash
# Check Cloud Build logs
gcloud builds list --limit=10
gcloud builds log <build-id>

# Common issues:
# - Missing dependencies in requirements.txt
# - Syntax errors in code
# - Docker build context issues
```

### Deployment Fails

```bash
# Check Cloud Run logs
gcloud run services describe payment-service --region=us-east1

# Common issues:
# - Invalid config.json
# - Missing permissions
# - Port not set to 8080
```

### Service Not Discovered

```bash
# Check if service is running
gcloud run services list --region=us-east1

# Refresh API Gateway
# Redeploy API Gateway:
python -m deploy.cli deploy api-gateway --force

# Or wait a few minutes for auto-discovery
```

### High Costs

```bash
# Check current costs
gcloud billing accounts list

# Common cost issues:
# - Min instances > 0 (should be 0)
# - Large memory allocation (reduce if possible)
# - Too many builds (use caching)
```

---

## Reference

### File Structure

```
gcp-graphql/
├── base-images/         # Base Docker images
├── cicd/                # CI/CD system
├── core-services/       # Infrastructure services
│   └── api-gateway/
├── deploy/              # Deployment system
├── docs/                # Documentation
├── infrastructure/      # Terraform
├── services/            # Your microservices
├── shared/              # SDK libraries
└── tools/               # Utilities
```

### Commands Reference

**Deployment:**
- `python -m deploy.cli deploy <service>`
- `python -m deploy.cli status`
- `python -m deploy.cli list`
- `python -m deploy.cli rollback <service> <version>`
- `python -m deploy.cli services`
- `python -m deploy.cli images`

**CI/CD:**
- `python -m cicd.cli setup`
- `python -m cicd.cli list`
- `python -m cicd.cli run <trigger-id>`
- `python -m cicd.cli delete <trigger-id>`

**Service Creation:**
- `python tools/create_service.py <name> --lang python`
- `python tools/create_service.py <name> --lang nodejs`

**Infrastructure:**
- `terraform init`
- `terraform plan`
- `terraform apply`
- `terraform destroy`

### Configuration Files

**config.json** (project root):
```json
{
  "project_id": "true-ability-399619 ",
  "region": "us-east1"
}
```

**config.json** (per service):
```json
{
  "memory": "512Mi",
  "cpu": "1",
  "timeout": 60,
  "min_instances": 0,
  "max_instances": 100
}
```

### Cost Breakdown

| Component | Idle | Active (1M req/mo) |
|-----------|------|-------------------|
| Cloud Run | $0 | ~$40 |
| Artifact Registry | ~$0.50 | ~$0.50 |
| Cloud Storage | ~$1 | ~$2 |
| Cloud Build | $0 | ~$5 |
| **Total** | **~$2-3** | **~$50** |

---

## Next Steps

1. ✅ Platform deployed and running
2. 🔜 Create more microservices
3. 🔜 Build DB service (SQLite + Cloud Storage)
4. 🔜 Build storage service
5. 🔜 Add UI frontends
6. 🔜 Implement full GraphQL Federation

---

**You're all set! Start building amazing microservices! 🚀**
