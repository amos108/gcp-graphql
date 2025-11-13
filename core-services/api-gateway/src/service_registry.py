"""
Service Registry - Discovers and tracks available microservices

Uses Cloud Run API to discover running services and their URLs.
"""

import os
from typing import Dict, Optional
import httpx
from google.cloud import run_v2
from google.api_core import exceptions


class ServiceRegistry:
    """
    Discover and track available microservices.

    Automatically discovers services from Cloud Run in the same project/region.
    Caches service URLs for fast lookup.
    """

    def __init__(self, project_id: str, region: str):
        self.project_id = project_id
        self.region = region
        self.services: Dict[str, str] = {}
        self.client = run_v2.ServicesClient()

    async def discover_services(self):
        """
        Discover services from Cloud Run.

        Populates self.services with {service_name: service_url}
        """
        # First, check environment variables for local development
        self._load_from_env()

        # Then, discover from Cloud Run
        try:
            await self._discover_from_cloud_run()
        except Exception as e:
            print(f"Warning: Could not discover Cloud Run services: {e}")

    def _load_from_env(self):
        """Load service URLs from environment variables"""
        # Common service patterns
        service_patterns = [
            'DB_SERVICE_URL',
            'STORAGE_SERVICE_URL',
            'UI_AUTOMATION_SERVICE_URL',
            'QUERY_SERVICE_URL',
            'PAYMENT_SERVICE_URL',
            'ORDER_SERVICE_URL',
            'EMAIL_SERVICE_URL',
            'AUTH_SERVICE_URL'
        ]

        for env_var in service_patterns:
            url = os.getenv(env_var)
            if url:
                # Convert env var to service name
                # e.g., DB_SERVICE_URL -> db-service
                service_name = env_var.replace('_SERVICE_URL', '').lower().replace('_', '-')
                self.services[service_name] = url

    async def _discover_from_cloud_run(self):
        """Discover services from Cloud Run API"""
        parent = f'projects/{self.project_id}/locations/{self.region}'

        try:
            # List all Cloud Run services
            for service in self.client.list_services(parent=parent):
                service_name = service.name.split('/')[-1]

                # Don't include self (api-gateway)
                if service_name == 'api-gateway':
                    continue

                # Add service URL
                if service.uri:
                    self.services[service_name] = service.uri

        except exceptions.PermissionDenied:
            print("Warning: No permission to list Cloud Run services")
        except Exception as e:
            print(f"Error discovering services: {e}")

    def get_service_url(self, service_name: str) -> Optional[str]:
        """
        Get URL for a service.

        Args:
            service_name: Name of the service

        Returns:
            Service URL or None if not found
        """
        return self.services.get(service_name)

    async def call_service(
        self,
        service_name: str,
        query: str,
        variables: Optional[Dict] = None,
        run_id: Optional[str] = None
    ) -> Dict:
        """
        Call a service via GraphQL.

        Args:
            service_name: Name of service to call
            query: GraphQL query/mutation
            variables: Query variables
            run_id: Run ID for tracing

        Returns:
            Response data

        Raises:
            ValueError: If service not found
            httpx.HTTPError: If request fails
        """
        url = self.get_service_url(service_name)

        if not url:
            raise ValueError(
                f"Service {service_name} not found. "
                f"Available: {list(self.services.keys())}"
            )

        # Ensure URL has /graphql endpoint
        if not url.endswith('/graphql'):
            url = f'{url}/graphql'

        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'api-gateway/0.1.0'
        }

        if run_id:
            headers['X-Run-ID'] = run_id

        # Make request
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json={
                    'query': query,
                    'variables': variables or {}
                },
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            # Check for GraphQL errors
            if 'errors' in result:
                raise Exception(f"GraphQL errors from {service_name}: {result['errors']}")

            return result.get('data', {})

    async def health_check(self, service_name: str) -> bool:
        """
        Check if a service is healthy.

        Args:
            service_name: Name of service to check

        Returns:
            True if healthy, False otherwise
        """
        url = self.get_service_url(service_name)

        if not url:
            return False

        # Try to hit health endpoint
        health_url = f'{url}/health'

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                return response.status_code == 200
        except:
            return False

    def list_services(self) -> Dict[str, str]:
        """
        List all registered services.

        Returns:
            Dictionary of {service_name: service_url}
        """
        return self.services.copy()

    async def refresh(self):
        """Refresh service discovery"""
        self.services.clear()
        await self.discover_services()
