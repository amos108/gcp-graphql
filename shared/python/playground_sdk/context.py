"""RunContext for execution tracking with run_id"""

from contextvars import ContextVar
from typing import Optional, Dict, Any
import secrets
from datetime import datetime

# Thread-safe run context storage
_run_context: ContextVar[Optional['RunContext']] = ContextVar('run_context', default=None)


class RunContext:
    """
    Execution context with run_id tracking.

    Every execution gets a unique run_id that is propagated across all services.
    This enables complete traceability of what happened during an execution.

    Example:
        ```python
        # Create new run context
        run = RunContext()
        print(run.run_id)  # exec_20250113103045_a7b3c9d2

        # Or get current context
        run = RunContext.get_current()

        # Use as context manager
        with RunContext() as run:
            # All operations in this block tagged with run.run_id
            pass
        ```
    """

    def __init__(self, run_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize RunContext.

        Args:
            run_id: Optional run_id. If not provided, generates new one.
            metadata: Optional metadata dictionary to attach to this run.
        """
        self.run_id = run_id or self._generate_run_id()
        self.metadata = metadata or {}
        self._token = None

    @staticmethod
    def _generate_run_id() -> str:
        """
        Generate unique run_id.

        Format: exec_{timestamp}_{random}
        Example: exec_20250113103045_a7b3c9d2

        Returns:
            Unique run_id string
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_hex = secrets.token_hex(4)
        return f'exec_{timestamp}_{random_hex}'

    @classmethod
    def get_current(cls) -> 'RunContext':
        """
        Get current run context from context variable.

        If no context exists, creates a new one.

        Returns:
            Current RunContext instance
        """
        ctx = _run_context.get()
        if ctx is None:
            ctx = cls()
            _run_context.set(ctx)
        return ctx

    @classmethod
    def set_current(cls, context: 'RunContext'):
        """
        Set current run context.

        Args:
            context: RunContext to set as current
        """
        _run_context.set(context)

    def set_metadata(self, key: str, value: Any):
        """
        Attach metadata to this run.

        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get metadata value.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def __enter__(self):
        """Context manager entry - sets this as current context"""
        self._token = _run_context.set(self)
        return self

    def __exit__(self, *args):
        """Context manager exit - resets context"""
        if self._token:
            _run_context.reset(self._token)

    def __repr__(self):
        return f'RunContext(run_id={self.run_id})'


# Convenience functions

def get_run_id() -> str:
    """
    Get current run_id.

    Returns:
        Current run_id string
    """
    return RunContext.get_current().run_id


def set_run_id(run_id: str):
    """
    Set run_id for current context.

    Args:
        run_id: Run ID to set
    """
    ctx = RunContext(run_id=run_id)
    RunContext.set_current(ctx)


def get_metadata(key: str, default: Any = None) -> Any:
    """
    Get metadata from current run context.

    Args:
        key: Metadata key
        default: Default value

    Returns:
        Metadata value or default
    """
    return RunContext.get_current().get_metadata(key, default)


def set_metadata(key: str, value: Any):
    """
    Set metadata in current run context.

    Args:
        key: Metadata key
        value: Metadata value
    """
    RunContext.get_current().set_metadata(key, value)
