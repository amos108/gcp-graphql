"""
API Gateway - GraphQL Federation and Service Discovery

Routes requests to microservices and injects run_id for tracing.
"""
import sys
import os
from pathlib import Path

# Add shared SDK to path
# In Docker: /app/shared/python (2 levels up from src/)
# In dev: ../../../../shared/python (4 levels up from src/)
docker_sdk_path = Path(__file__).parent.parent / "shared" / "python"
dev_sdk_path = Path(__file__).parent.parent.parent.parent / "shared" / "python"

if docker_sdk_path.exists():
    shared_sdk_path = docker_sdk_path
elif dev_sdk_path.exists():
    shared_sdk_path = dev_sdk_path
else:
    raise ImportError(f"Could not find playground_sdk. Tried: {docker_sdk_path}, {dev_sdk_path}")

sys.path.insert(0, str(shared_sdk_path))

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import from shared SDK
from playground_sdk import RunContext, get_run_id, set_run_id, setup_logging, setup_tracing
from playground_sdk.logging import get_logger

# OpenTelemetry instrumentation
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    print("Warning: OpenTelemetry instrumentation not available")

# Import service discovery
# Add parent directory to path for src imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.service_registry import ServiceRegistry
from src.federation import FederationComposer

# Setup structured logging (JSON format in production, human-readable in dev)
is_dev = os.getenv('DEBUG', 'false').lower() == 'true'
logger = setup_logging('api-gateway', level=os.getenv('LOG_LEVEL', 'INFO'), structured=not is_dev)

# Setup OpenTelemetry tracing
tracer = setup_tracing('api-gateway', enable_cloud_trace=not is_dev)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("=" * 80)
    print("LIFESPAN FUNCTION CALLED - STARTUP BEGINNING")
    print("=" * 80)
    logger.info("API Gateway starting up...")

    # Initialize service registry
    app.state.registry = ServiceRegistry(
        project_id=os.getenv('GCP_PROJECT', 'true-ability-399619'),
        region=os.getenv('GCP_REGION', 'us-east1')
    )

    # Discover services
    await app.state.registry.discover_services()

    logger.info(f"Discovered {len(app.state.registry.services)} services")

    # Filter to only GraphQL backend services (exclude ui-* services)
    graphql_services = {
        name: url for name, url in app.state.registry.services.items()
        if not name.startswith('ui-')
    }

    logger.info(f"GraphQL services for federation: {list(graphql_services.keys())}")

    # Initialize GraphQL Federation composer
    # Configure run storage service URL if available
    run_storage_url = os.getenv('RUN_STORAGE_URL', 'http://localhost:8082')
    app.state.federation = FederationComposer(run_storage_url=run_storage_url)
    logger.info(f"Run storage service URL: {run_storage_url}")

    # Fetch and compose GraphQL schemas from subgraph services
    await app.state.federation.fetch_subgraph_schemas(graphql_services)

    logger.info("GraphQL Federation initialized")

    yield

    logger.info("API Gateway shutting down...")


# Create FastAPI app
app = FastAPI(
    title="GCP Microservices Playground API Gateway",
    description="GraphQL Federation Gateway with Service Discovery",
    version="0.1.0",
    lifespan=lifespan
)

# Add OpenTelemetry instrumentation
if OTEL_AVAILABLE:
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    logger.info("OpenTelemetry instrumentation enabled")

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


@app.get("/federation/debug")
async def federation_debug(request: Request):
    """Debug endpoint to see federation configuration"""
    federation = request.app.state.federation

    return {
        "federation_info": federation.get_composed_schema_info(),
        "all_services": request.app.state.registry.services
    }


@app.get("/graphql")
async def graphql_playground(request: Request):
    """
    GraphQL Playground - Interactive GraphQL IDE.
    Access this in your browser to test GraphQL queries.
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>GraphQL Playground - API Gateway</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
        <link rel="shortcut icon" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/favicon.png" />
        <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
    </head>
    <body>
        <div id="root"></div>
        <script>
            window.addEventListener('load', function (event) {
                GraphQLPlayground.init(document.getElementById('root'), {
                    endpoint: '/graphql',
                    settings: {
                        'request.credentials': 'same-origin',
                    },
                    tabs: [
                        {
                            endpoint: '/graphql',
                            name: 'Federated Query Example',
                            query: `# Example federated query across multiple services\\n# Query users with their posts and comments\\n\\nquery GetUsersWithPostsAndComments {\\n  users {\\n    id\\n    name\\n    email\\n    posts {\\n      id\\n      title\\n      content\\n      comments {\\n        id\\n        text\\n        author {\\n          name\\n        }\\n      }\\n    }\\n    comments {\\n      id\\n      text\\n      post {\\n        title\\n      }\\n    }\\n  }\\n}\\n\\n# Query a specific post with author and comments\\nquery GetPostDetails {\\n  post(id: "1") {\\n    id\\n    title\\n    content\\n    author {\\n      name\\n      email\\n    }\\n    comments {\\n      id\\n      text\\n      author {\\n        name\\n      }\\n    }\\n  }\\n}\\n\\n# Create a new post\\nmutation CreatePost {\\n  createPost(input: {\\n    title: "New Post"\\n    content: "This is a new post created via GraphQL"\\n    authorId: "1"\\n  }) {\\n    id\\n    title\\n    author {\\n      name\\n    }\\n  }\\n}`
                        }
                    ]
                })
            })
        </script>
    </body>
    </html>
    """
    return Response(content=html, media_type="text/html")


@app.post("/graphql")
async def graphql_endpoint(request: Request):
    """
    GraphQL Federation endpoint.

    Executes GraphQL queries across multiple federated subgraph services,
    automatically routing queries to the appropriate services and merging results.
    """
    federation: FederationComposer = request.app.state.federation
    run_id = request.state.run_id

    body = await request.json()
    query = body.get('query', '')
    variables = body.get('variables', {})

    # Execute federated query
    result = await federation.execute_federated_query(query, variables, run_id)

    return result


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
