"""Service Router for discovering and calling microservices"""

import os
import httpx
from typing import Dict, Optional, Any
from .context import get_run_id


class ServiceRouter:
    """
    Route requests to local or remote services.

    Automatically discovers whether services are running locally or remotely
    and routes requests accordingly.

    Example:
        ```python
        from playground_sdk import router

        # Call a service
        result = await router.call_service('db-service', '''
            mutation {
                insert(table: "orders", data: {amount: 99.99}) {
                    id
                }
            }
        ''', {'amount': 99.99})
        ```
    """

    def __init__(self):
        self.local_service = os.getenv('LOCAL_SERVICE')
        self._service_urls: Dict[str, str] = {}
        self._load_service_urls()

    def _load_service_urls(self):
        """Load service URLs from environment variables"""
        # Common services that might exist
        potential_services = [
            'api-gateway',
            'db-service',
            'storage-service',
            'ui-automation-service',
            'query-service',
            'payment-service',
            'order-service',
            'email-service',
            'auth-service',
        ]

        for service in potential_services:
            env_var = service.upper().replace('-', '_') + '_URL'

            # Check if this service is running locally
            if service == self.local_service:
                self._service_urls[service] = os.getenv(env_var, 'http://localhost:8080')
            else:
                # Use remote URL from environment if available
                url = os.getenv(env_var)
                if url:
                    self._service_urls[service] = url

    def register_service(self, name: str, url: str):
        """
        Manually register a service URL.

        Args:
            name: Service name (e.g., 'payment-service')
            url: Service URL (e.g., 'https://payment-service-xxx.run.app')
        """
        self._service_urls[name] = url

    def get_url(self, service_name: str) -> Optional[str]:
        """
        Get URL for a service.

        Args:
            service_name: Name of the service

        Returns:
            Service URL or None if not found
        """
        return self._service_urls.get(service_name)

    async def call_service(
        self,
        service_name: str,
        query: str,
        variables: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Call a service via GraphQL.

        Args:
            service_name: Name of the service to call
            query: GraphQL query or mutation
            variables: Variables for the query
            timeout: Request timeout in seconds

        Returns:
            Response data dictionary

        Raises:
            ValueError: If service not found
            httpx.HTTPError: If request fails
        """
        url = self.get_url(service_name)

        if not url:
            raise ValueError(f"Service {service_name} not found. Available: {list(self._service_urls.keys())}")

        # Ensure URL has /graphql endpoint
        if not url.endswith('/graphql'):
            url = f'{url}/graphql'

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                json={
                    'query': query,
                    'variables': variables or {}
                },
                headers=self._get_headers()
            )

            response.raise_for_status()
            result = response.json()

            # Check for GraphQL errors
            if 'errors' in result:
                raise Exception(f"GraphQL errors: {result['errors']}")

            return result.get('data', {})

    async def call_rest(
        self,
        service_name: str,
        path: str,
        method: str = 'GET',
        data: Optional[Dict] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Call a service via REST API.

        Args:
            service_name: Name of the service to call
            path: API path (e.g., '/api/users')
            method: HTTP method (GET, POST, PUT, DELETE)
            data: Request data for POST/PUT
            timeout: Request timeout in seconds

        Returns:
            Response data dictionary

        Raises:
            ValueError: If service not found
            httpx.HTTPError: If request fails
        """
        url = self.get_url(service_name)

        if not url:
            raise ValueError(f"Service {service_name} not found")

        # Construct full URL
        full_url = f'{url.rstrip("/")}/{path.lstrip("/")}'

        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == 'GET':
                response = await client.get(full_url, headers=self._get_headers())
            elif method.upper() == 'POST':
                response = await client.post(full_url, json=data, headers=self._get_headers())
            elif method.upper() == 'PUT':
                response = await client.put(full_url, json=data, headers=self._get_headers())
            elif method.upper() == 'DELETE':
                response = await client.delete(full_url, headers=self._get_headers())
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for requests with run_id.

        Returns:
            Headers dictionary
        """
        return {
            'X-Run-ID': get_run_id(),
            'Content-Type': 'application/json',
            'User-Agent': 'playground-sdk/0.1.0'
        }

    def list_services(self) -> Dict[str, str]:
        """
        List all registered services.

        Returns:
            Dictionary of service_name -> url
        """
        return self._service_urls.copy()


# Global router instance
router = ServiceRouter()
