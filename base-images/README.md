# Base Docker Images

Pre-built base images with common dependencies for microservices.

## Why Base Images?

Base images significantly speed up service builds:

- **Without base images**: 2-3 minutes per service
- **With base images**: 5-10 seconds per service ⚡

## Available Base Images

### Python (`python-playground`)

- **Base**: Python 3.11-slim
- **Includes**:
  - FastAPI + Uvicorn
  - Strawberry GraphQL
  - Google Cloud SDK (Storage, Logging)
  - OpenTelemetry
  - playground_sdk

### Node.js (`nodejs-playground`)

- **Base**: Node.js 20-slim
- **Includes**:
  - Express + Apollo Server
  - GraphQL
  - Google Cloud SDK
  - OpenTelemetry
  - Common utilities

### Go (`go-playground`)

- **Base**: Go 1.21 + Alpine
- **Includes**:
  - gqlgen (GraphQL)
  - Google Cloud SDK
  - OpenTelemetry
  - Common packages

## Building Base Images

### Prerequisites

1. Terraform infrastructure deployed
2. Authenticated with GCP

### Build All Images

**On Linux/Mac:**
```bash
cd base-images
chmod +x build-all.sh
./build-all.sh
```

**On Windows:**
```powershell
cd base-images
.\build-all.ps1
```

### Build Individual Image

```bash
cd base-images/python-playground
gcloud builds submit \
  --tag us-east1-docker.pkg.dev/true-ability-399619 /base-images/python-playground:latest
```

## Using Base Images in Services

Services automatically use base images when deployed with buildpacks or can reference them in Dockerfiles:

```dockerfile
FROM us-east1-docker.pkg.dev/true-ability-399619 /base-images/python-playground:latest

COPY src/ ./src/
CMD ["python", "-m", "src.main"]
```

## Updating Base Images

Base images should be updated when:

1. Adding new common dependencies
2. Updating Python/Node/Go versions
3. Security updates
4. playground_sdk updates

### CI/CD Automation

GitHub Actions automatically rebuilds base images when:
- Base image files change
- shared/python/playground_sdk changes
- Push to main branch

## Cost

Base image storage costs ~$0.10/GB/month in Artifact Registry.

Typical sizes:
- Python: ~200MB
- Node.js: ~150MB
- Go: ~40MB

**Total**: ~$0.04/month
