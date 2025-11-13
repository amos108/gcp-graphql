"""OpenTelemetry tracing setup for Cloud Trace"""

import os
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from .context import get_run_id


def setup_tracing(
    service_name: str,
    service_version: str = "0.1.0",
    enable_cloud_trace: bool = True
) -> trace.Tracer:
    """
    Setup OpenTelemetry tracing with Cloud Trace export.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        enable_cloud_trace: Whether to export to Cloud Trace

    Returns:
        Configured tracer instance

    Example:
        ```python
        from playground_sdk import setup_tracing

        # In your service startup
        tracer = setup_tracing('payment-service')

        # Use in handlers
        with tracer.start_as_current_span('process_payment'):
            # Your code here
            pass
        ```
    """
    # Create resource with service info
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add Cloud Trace exporter if enabled
    if enable_cloud_trace and os.getenv('GCP_PROJECT'):
        try:
            from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

            # Cloud Trace exporter
            cloud_trace_exporter = CloudTraceSpanExporter(
                project_id=os.getenv('GCP_PROJECT')
            )

            # Add batch processor
            provider.add_span_processor(
                BatchSpanProcessor(cloud_trace_exporter)
            )
        except ImportError:
            # Cloud Trace exporter not installed, skip
            pass

    # Set as global tracer provider
    trace.set_tracer_provider(provider)

    # Return tracer for this service
    return trace.get_tracer(service_name, service_version)


def get_tracer(service_name: Optional[str] = None) -> trace.Tracer:
    """
    Get tracer instance.

    Args:
        service_name: Optional service name, defaults to current service

    Returns:
        Tracer instance

    Example:
        ```python
        from playground_sdk import get_tracer

        tracer = get_tracer()

        with tracer.start_as_current_span('my_operation'):
            # Your code
            pass
        ```
    """
    if not service_name:
        service_name = os.getenv('SERVICE_NAME', 'unknown-service')

    return trace.get_tracer(service_name)


def add_span_attributes(**attributes):
    """
    Add attributes to current span.

    Args:
        **attributes: Key-value pairs to add to span

    Example:
        ```python
        from playground_sdk import add_span_attributes, get_run_id

        add_span_attributes(
            user_id=123,
            run_id=get_run_id(),
            amount=99.99
        )
        ```
    """
    span = trace.get_current_span()
    if span:
        for key, value in attributes.items():
            span.set_attribute(key, value)


def trace_function(operation_name: Optional[str] = None):
    """
    Decorator to automatically trace a function.

    Args:
        operation_name: Optional name for the operation

    Returns:
        Decorator function

    Example:
        ```python
        from playground_sdk import trace_function

        @trace_function("payment_processing")
        async def process_payment(amount: float):
            # Automatically traced
            pass
        ```
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_tracer()
            span_name = operation_name or func.__name__

            with tracer.start_as_current_span(span_name) as span:
                # Add run_id to span
                span.set_attribute('run_id', get_run_id())

                # Call original function
                result = await func(*args, **kwargs)
                return result

        return wrapper

    return decorator
