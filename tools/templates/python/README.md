# {{SERVICE_NAME}}

{{SERVICE_DESCRIPTION}}

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Install playground SDK
pip install -e ../../shared/python/playground_sdk

# Set environment variables
export SERVICE_NAME={{SERVICE_NAME}}
export GCP_PROJECT=globalwinner
export GCP_REGION=us-east1
export DEBUG=true

# Run locally
python -m src.main
```

Server starts at http://localhost:8080

### Test Endpoints

```bash
# Health check
curl http://localhost:8080/health

# Root
curl http://localhost:8080/

# GraphQL
curl -X POST http://localhost:8080/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ exampleQuery(id: 1) }"}'
```

## Deploy

```bash
# Deploy to production
python -m deploy.cli deploy {{SERVICE_NAME}}

# Deploy to staging
python -m deploy.cli deploy {{SERVICE_NAME}} --env staging

# Force rebuild
python -m deploy.cli deploy {{SERVICE_NAME}} --force
```

## Adding Functionality

### 1. Add a new handler in `src/handlers.py`

```python
@handler
async def my_new_function(run: RunContext, param: str):
    logger.info(f"New function called: {param}")

    # Your logic here
    result = {"message": f"Processed {param}"}

    return result
```

### 2. Call other services

```python
@handler
async def create_order(run: RunContext, order_data: dict):
    # Call db-service
    db_result = await router.call_service('db-service', '''
        mutation {
            insert(table: "orders", data: $data) {
                id
            }
        }
    ''', {'data': order_data})

    return db_result
```

### 3. Use tracing

```python
from playground_sdk import get_tracer

tracer = get_tracer()

@handler
async def tracked_operation(run: RunContext):
    with tracer.start_as_current_span('my_operation'):
        # Your code here
        pass
```

## Configuration

Edit `config.json` to change:
- Memory/CPU limits
- Scaling (min/max instances)
- Environment variables
- Timeout

## Logs

View logs:
```bash
# In GCP Console: Cloud Run > {{SERVICE_NAME}} > Logs

# Or use gcloud:
gcloud run services logs read {{SERVICE_NAME}} --limit=100
```

## Monitoring

All operations are automatically:
- Tagged with run_id
- Traced with OpenTelemetry
- Logged with structured JSON
- Monitored in Cloud Trace/Logging

Query everything from a run:
```bash
# In Cloud Console, search for:
# run_id="exec_20250113_abc123"
```
