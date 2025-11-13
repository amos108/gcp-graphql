# {{SERVICE_NAME}}

{{SERVICE_DESCRIPTION}}

## Quick Start

### Local Development

```bash
# Install dependencies
npm install

# Set environment variables
export SERVICE_NAME={{SERVICE_NAME}}
export PORT=8080

# Run locally
npm start

# Or with auto-reload
npm run dev
```

Server starts at http://localhost:8080

### Test Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Root
curl http://localhost:8080/

# Example API
curl -X POST http://localhost:8080/api/example \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

## Deploy

```bash
# Deploy to production
python -m deploy.cli deploy {{SERVICE_NAME}}

# Deploy to staging
python -m deploy.cli deploy {{SERVICE_NAME}} --env staging
```

## Development

Edit `src/index.js` to add your business logic.

All requests automatically get `run_id` for tracing!
