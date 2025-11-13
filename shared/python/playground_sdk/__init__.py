"""
GCP Microservices Playground SDK

This SDK provides common functionality for all microservices:
- RunContext: Execution tracking with run_id
- Service Router: Local/remote service discovery
- Tracing: OpenTelemetry integration
- Logging: Structured logging
- Decorators: Handler decorators for easy service creation
"""

__version__ = "0.1.0"

from .context import RunContext, get_run_id, set_run_id
from .router import ServiceRouter, router
from .decorators import handler, mutation, query
from .tracing import setup_tracing, get_tracer
from .logging import setup_logging, get_logger

__all__ = [
    'RunContext',
    'get_run_id',
    'set_run_id',
    'ServiceRouter',
    'router',
    'handler',
    'mutation',
    'query',
    'setup_tracing',
    'get_tracer',
    'setup_logging',
    'get_logger',
]
