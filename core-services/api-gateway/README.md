# API Gateway

GraphQL Federation Gateway with automatic service discovery.

## Features

- ✅ **Auto Service Discovery**: Discovers Cloud Run services automatically
- ✅ **run_id Injection**: Automatically generates or propagates run_id
- ✅ **Service Routing**: Routes requests to appropriate microservices
- ✅ **Health Checks**: Monitor service availability
- ✅ **CORS Support**: Configurable CORS for web clients

## Endpoints

### `GET /`
Root endpoint with service info.

### `GET /health`
Health check endpoint.

### `GET /services`
List all discovered services.

**Response:**
```json
{
  "services": [
    {
      "name": "db-service",
      "url": "https://db-service-xxx.run.app",
      "status": "available"
    }
  ],
  "count": 1
}
```

### `POST /graphql`
GraphQL endpoint (Federation coming soon).

### `POST /call/{service_name}`
Direct service call endpoint.

**Example:**
```bash
curl -X POST https://api-gateway-xxx.run.app/call/db-service \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { insert(table: \"users\", data: {name: \"John\"}) { id } }"
  }'
```

## Service Discovery

The API Gateway discovers services in two ways:

### 1. Environment Variables (Local Development)

```bash
export DB_SERVICE_URL=http://localhost:8081
export STORAGE_SERVICE_URL=http://localhost:8082
export PAYMENT_SERVICE_URL=http://localhost:8083
```

### 2. Cloud Run API (Production)

Automatically discovers all Cloud Run services in the same project/region.

## run_id Propagation

Every request gets a `run_id` for tracing:

```
Request → API Gateway
         ↓
    Generate/Extract run_id
         ↓
    Add X-Run-ID header
         ↓
    Forward to service
         ↓
    Add X-Run-ID to response
```

**Client can provide run_id:**
```bash
curl -H "X-Run-ID: exec_20250113_abc123" ...
```

**Or Gateway generates one:**
```
X-Run-ID: exec_20250113_a7b3c9d2
```

## Local Development

```bash
cd core-services/api-gateway

# Install dependencies
pip install -r requirements.txt

# Set environment
export GCP_PROJECT=globalwinner
export GCP_REGION=us-east1
export DEBUG=true

# Run locally
python -m src.main
```

Server starts at http://localhost:8080

## Deployment

### Using Deploy CLI

```bash
# Deploy API Gateway
python -m deploy.cli deploy api-gateway

# Deploy to staging
python -m deploy.cli deploy api-gateway --env staging
```

### Using Cloud Build

```bash
cd core-services/api-gateway
gcloud builds submit --config cloudbuild.yaml
```

## Configuration

Edit `config.json`:

```json
{
  "memory": "512Mi",
  "cpu": "1",
  "timeout": 60,
  "min_instances": 0,
  "max_instances": 100,
  "allow_unauthenticated": true,
  "env": {
    "production": {
      "GCP_PROJECT": "globalwinner",
      "GCP_REGION": "us-east1",
      "LOG_LEVEL": "INFO"
    }
  }
}
```

## Adding New Services

Services are automatically discovered when deployed to Cloud Run in the same project/region.

No configuration needed!

## GraphQL Federation (Coming Soon)

Future features:
- Automatic schema composition from services
- Type merging across services
- Intelligent query planning
- Distributed execution

## Architecture

```
Client
  ↓
API Gateway (Cloud Run)
  ├─ Service Discovery (Cloud Run API)
  ├─ run_id Generation/Propagation
  ├─ Request Routing
  └─ Response Aggregation
  ↓
Microservices (Cloud Run)
  ├─ db-service
  ├─ storage-service
  ├─ payment-service
  └─ ...
```

## Monitoring

View logs:
```bash
# In GCP Console: Cloud Run > api-gateway > Logs

# Or use gcloud:
gcloud run services logs read api-gateway --limit=100
```

## Cost

- **Idle**: $0 (scales to zero)
- **Active**: ~$0.40 per million requests
- **Memory**: 512Mi (included in request cost)

## Next Steps

1. Deploy API Gateway: `python -m deploy.cli deploy api-gateway`
2. Check services: `curl https://api-gateway-xxx.run.app/services`
3. Deploy microservices (they'll be auto-discovered)
4. Call services through gateway
