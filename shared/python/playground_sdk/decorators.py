"""Decorators for easy service handler creation"""

from functools import wraps
from typing import Callable, Any
from .context import RunContext


def handler(func: Callable) -> Callable:
    """
    Decorator for service handlers - auto-injects RunContext.

    The decorated function receives RunContext as the first parameter,
    which contains the run_id and metadata for this execution.

    Example:
        ```python
        from playground_sdk import handler, RunContext

        @handler
        async def my_function(run: RunContext, amount: float, user_id: int):
            print(f"Running in: {run.run_id}")
            # Your logic here
            return {"success": True}
        ```

    Args:
        func: Async function to decorate

    Returns:
        Wrapped function with RunContext injection
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract run_id from kwargs if provided
        run_id = kwargs.pop('run_id', None)

        # Create or get run context
        if run_id:
            run_ctx = RunContext(run_id)
        else:
            run_ctx = RunContext.get_current()

        # Set context and call handler
        with run_ctx:
            # Inject run context as first parameter
            return await func(run_ctx, *args, **kwargs)

    return wrapper


def mutation(func: Callable) -> Callable:
    """
    Decorator for GraphQL mutations - same as @handler.

    This is an alias for @handler to make GraphQL code more readable.

    Example:
        ```python
        from playground_sdk import mutation, RunContext

        @mutation
        async def create_order(run: RunContext, amount: float):
            # Your mutation logic
            return {"order_id": 123}
        ```
    """
    return handler(func)


def query(func: Callable) -> Callable:
    """
    Decorator for GraphQL queries - same as @handler.

    This is an alias for @handler to make GraphQL code more readable.

    Example:
        ```python
        from playground_sdk import query, RunContext

        @query
        async def get_order(run: RunContext, order_id: int):
            # Your query logic
            return {"id": order_id, "status": "processing"}
        ```
    """
    return handler(func)


def trace_operation(operation_name: str):
    """
    Decorator to trace specific operations with custom name.

    Example:
        ```python
        from playground_sdk import trace_operation, RunContext

        @trace_operation("payment_processing")
        async def process_payment(run: RunContext, amount: float):
            # This operation will be traced as "payment_processing"
            pass
        ```

    Args:
        operation_name: Name for the traced operation

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get or create run context
            run_ctx = RunContext.get_current()

            # Store operation name in metadata
            run_ctx.set_metadata('operation', operation_name)

            # Call original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def requires_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for a handler.

    Checks for user information in RunContext metadata.
    If not found, raises ValueError.

    Example:
        ```python
        from playground_sdk import handler, requires_auth, RunContext

        @handler
        @requires_auth
        async def protected_function(run: RunContext, data: dict):
            user_id = run.get_metadata('user_id')
            # Your protected logic
            pass
        ```

    Args:
        func: Function to decorate

    Returns:
        Wrapped function with auth check
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        run_ctx = RunContext.get_current()

        # Check for user authentication in metadata
        user_id = run_ctx.get_metadata('user_id')
        if not user_id:
            raise ValueError("Authentication required - no user_id in run context")

        return await func(*args, **kwargs)

    return wrapper
