"""
{{SERVICE_NAME}} - Python Microservice Template

This is a template for creating Python microservices using the playground SDK.
"""

import os
import sys
from pathlib import Path
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Add playground SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / 'shared' / 'python'))

from playground_sdk import (
    RunContext,
    setup_logging,
    setup_tracing,
    router
)

# Import handlers
from handlers import resolvers

# Setup logging and tracing
logger = setup_logging('{{SERVICE_NAME}}', level=os.getenv('LOG_LEVEL', 'INFO'))
tracer = setup_tracing('{{SERVICE_NAME}}')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("{{SERVICE_NAME}} starting up...")
    yield
    logger.info("{{SERVICE_NAME}} shutting down...")


# Create FastAPI app
app = FastAPI(
    title="{{SERVICE_NAME}}",
    description="{{SERVICE_DESCRIPTION}}",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "{{SERVICE_NAME}}",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/graphql")
async def graphql_endpoint(request):
    """GraphQL endpoint - routes to handlers"""
    from playground_sdk import RunContext

    # Get run_id from header or create new
    run_id = request.headers.get('X-Run-ID')
    if run_id:
        run_ctx = RunContext(run_id=run_id)
    else:
        run_ctx = RunContext()

    RunContext.set_current(run_ctx)

    body = await request.json()
    query = body.get('query', '')
    variables = body.get('variables', {})

    # Simple query routing
    # TODO: Implement proper GraphQL schema with Strawberry

    return {
        "data": {
            "message": "GraphQL endpoint ready",
            "run_id": run_ctx.run_id
        }
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv('PORT', 8080))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv('DEBUG', 'false').lower() == 'true',
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )
