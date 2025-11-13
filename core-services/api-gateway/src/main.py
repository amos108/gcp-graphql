"""
API Gateway - GraphQL Federation and Service Discovery

Routes requests to microservices and injects run_id for tracing.
"""

import os
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import sys
from pathlib import Path

# Simple implementations replacing playground_sdk
import logging
from contextvars import ContextVar
import uuid

def setup_logging(service_name: str, level: str = 'INFO'):
    """Simple logging setup"""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
    return logger

def setup_tracing(service_name: str):
    """Simple tracer setup (no-op for now)"""
    return None

class RunContext:
    """Simple run context for tracking request IDs"""
    _current: ContextVar['RunContext'] = ContextVar('run_context', default=None)

    def __init__(self, run_id: str = None):
        self.run_id = run_id or str(uuid.uuid4())

    @classmethod
    def set_current(cls, context: 'RunContext'):
        cls._current.set(context)

    @classmethod
    def get_current(cls) -> 'RunContext':
        return cls._current.get()

# Import service discovery
from .service_registry import ServiceRegistry

logger = setup_logging('api-gateway', level=os.getenv('LOG_LEVEL', 'INFO'))
tracer = setup_tracing('api-gateway')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("API Gateway starting up...")

    # Initialize service registry
    app.state.registry = ServiceRegistry(
        project_id=os.getenv('GCP_PROJECT', 'true-ability-399619 '),
        region=os.getenv('GCP_REGION', 'us-east1')
    )

    # Discover services
    await app.state.registry.discover_services()

    logger.info(f"Discovered {len(app.state.registry.services)} services")

    yield

    logger.info("API Gateway shutting down...")


# Create FastAPI app
app = FastAPI(
    title="GCP Microservices Playground API Gateway",
    description="GraphQL Federation Gateway with Service Discovery",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def inject_run_id(request: Request, call_next):
    """
    Inject or extract run_id from requests.

    If X-Run-ID header exists, use it.
    Otherwise, generate new run_id.
    """
    run_id = request.headers.get('X-Run-ID')

    if not run_id:
        # Generate new run_id
        run_ctx = RunContext()
        run_id = run_ctx.run_id
    else:
        # Use existing run_id
        run_ctx = RunContext(run_id=run_id)

    # Set in context
    RunContext.set_current(run_ctx)

    # Add run_id to request state
    request.state.run_id = run_id

    # Call next middleware/endpoint
    response = await call_next(request)

    # Add run_id to response headers
    response.headers['X-Run-ID'] = run_id

    return response


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "API Gateway",
        "version": "0.1.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/services")
async def list_services(request: Request):
    """List all discovered services"""
    registry: ServiceRegistry = request.app.state.registry

    services = []
    for name, url in registry.services.items():
        services.append({
            "name": name,
            "url": url,
            "status": "available"
        })

    return {
        "services": services,
        "count": len(services)
    }


@app.post("/graphql")
async def graphql_endpoint(request: Request):
    """
    GraphQL endpoint - routes queries to appropriate services.

    For now, this is a simple passthrough.
    Later, implement GraphQL Federation for automatic schema composition.
    """
    registry: ServiceRegistry = request.app.state.registry
    run_id = request.state.run_id

    body = await request.json()
    query = body.get('query', '')
    variables = body.get('variables', {})

    # Simple routing based on query content
    # TODO: Implement proper GraphQL Federation

    # For now, return info about available services
    return {
        "data": {
            "services": list(registry.services.keys()),
            "run_id": run_id,
            "message": "GraphQL Federation coming soon. Use /services endpoint to see available services."
        }
    }


@app.post("/call/{service_name}")
async def call_service(service_name: str, request: Request):
    """
    Call a specific service directly.

    Useful for testing and direct service calls.
    """
    registry: ServiceRegistry = request.app.state.registry
    run_id = request.state.run_id

    # Get service URL
    service_url = registry.get_service_url(service_name)

    if not service_url:
        return {
            "error": f"Service {service_name} not found",
            "available_services": list(registry.services.keys())
        }, 404

    # Forward request to service
    body = await request.json()

    result = await registry.call_service(
        service_name=service_name,
        query=body.get('query', ''),
        variables=body.get('variables', {}),
        run_id=run_id
    )

    return result


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv('PORT', 8080))

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv('DEBUG', 'false').lower() == 'true',
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )
