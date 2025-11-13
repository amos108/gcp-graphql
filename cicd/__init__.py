"""
CI/CD automation using Google Cloud Build API

This package provides automated build triggers for:
- Base images
- Core services
- Microservices
"""

__version__ = "0.1.0"

from .trigger_manager import TriggerManager, BuildConfig

__all__ = ['TriggerManager', 'BuildConfig']
