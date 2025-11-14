"""Cloud Run API client for deploying services"""

from typing import Dict, Optional, List
from google.cloud import run_v2
from google.cloud.run_v2 import Service, Container, TrafficTarget, EnvVar
from google.api_core import exceptions
from google.iam.v1 import iam_policy_pb2, policy_pb2
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config

console = Console()


class CloudRunDeployer:
    """Deploy services to Cloud Run using API"""

    def __init__(self, config: Config):
        self.config = config
        self.client = run_v2.ServicesClient()

    async def deploy_service(self, service_name: str, image: str,
                            env: str, config: Dict) -> str:
        """Deploy service to Cloud Run"""

        console.print(f'[cyan] Deploying {service_name} to {env}...[/cyan]')

        # Try using gcloud CLI as it's more reliable
        return await self._deploy_with_gcloud(service_name, image, env, config)

    async def _deploy_with_gcloud(self, service_name: str, image: str, env: str, config: Dict) -> str:
        """Deploy service using gcloud CLI (fallback method)"""
        import subprocess
        import sys

        # Build gcloud command parts
        cmd_parts = [
            'gcloud', 'run', 'deploy', service_name,
            '--image', image,
            '--region', self.config.region,
            '--project', self.config.project_id,
            '--platform', 'managed',
            '--memory', config.get('memory', '512Mi'),
            '--cpu', config.get('cpu', '1'),
            '--timeout', str(config.get('timeout', 60)),
            '--min-instances', str(config.get('min_instances', 0)),
            '--max-instances', str(config.get('max_instances', 100)),
            '--quiet'
        ]

        # Add environment variables
        env_vars = self._build_env_vars(config, env)
        if env_vars:
            env_str = ','.join([f'{var.name}={var.value}' for var in env_vars])
            # Properly quote env vars for PowerShell to prevent concatenation
            cmd_parts.extend(['--set-env-vars', f'"{env_str}"'])

        # Add public access if configured
        if config.get('allow_unauthenticated', True):
            cmd_parts.append('--allow-unauthenticated')

        try:
            # On Windows, use powershell to run gcloud
            if sys.platform == 'win32':
                # Use array form to prevent argument mangling
                cmd_str = ' '.join(cmd_parts)
                cmd = ['powershell', '-Command', cmd_str]
            else:
                cmd = cmd_parts

            # Run gcloud command
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Get service URL
            url = await self._get_service_url(service_name)

            console.print(f'[green]+ Deployed to {url}[/green]')
            if config.get('allow_unauthenticated', True):
                console.print('[dim]+ Enabled public access[/dim]')

            return url

        except subprocess.CalledProcessError as e:
            console.print(f'[red]X gcloud deploy failed: {e.stderr}[/red]')
            raise RuntimeError(f"Deployment failed: {e.stderr}")

    async def _get_service_url(self, service_name: str) -> str:
        """Get URL for a deployed service"""
        service_path = f'projects/{self.config.project_id}/locations/{self.config.region}/services/{service_name}'

        try:
            service = self.client.get_service(name=service_path)
            return service.uri
        except:
            return f'https://{service_name}-{self.config.project_id}.{self.config.region}.run.app'

    async def _service_exists(self, service_path: str) -> bool:
        """Check if service already exists"""
        try:
            self.client.get_service(name=service_path)
            return True
        except exceptions.NotFound:
            return False
        except Exception:
            return False

    async def _set_public_access(self, service_path: str):
        """Allow unauthenticated access to service"""
        try:
            # Get current policy
            policy_request = iam_policy_pb2.GetIamPolicyRequest(
                resource=service_path
            )

            try:
                current_policy = self.client.get_iam_policy(request=policy_request)
            except:
                # If no policy exists, create empty one
                current_policy = policy_pb2.Policy()

            # Add allUsers as invoker
            binding_found = False
            for binding in current_policy.bindings:
                if binding.role == 'roles/run.invoker':
                    if 'allUsers' not in binding.members:
                        binding.members.append('allUsers')
                    binding_found = True
                    break

            if not binding_found:
                # Create new binding
                new_binding = policy_pb2.Binding(
                    role='roles/run.invoker',
                    members=['allUsers']
                )
                current_policy.bindings.append(new_binding)

            # Set the updated policy
            set_policy_request = iam_policy_pb2.SetIamPolicyRequest(
                resource=service_path,
                policy=current_policy
            )

            self.client.set_iam_policy(request=set_policy_request)
            console.print('[dim]+ Enabled public access[/dim]')

        except Exception as e:
            console.print(f'[yellow]Warning: Could not set public access: {e}[/yellow]')

    def _build_env_vars(self, config: Dict, env: str) -> List[EnvVar]:
        """Build environment variables for Cloud Run"""
        env_config = config.get('env', {}).get(env, {})

        # Add common env vars
        env_config['ENVIRONMENT'] = env
        env_config['GCP_PROJECT'] = self.config.project_id
        env_config['GCP_REGION'] = self.config.region

        # Convert to Cloud Run EnvVar format
        env_vars = []
        for key, value in env_config.items():
            env_vars.append(EnvVar(name=key, value=str(value)))

        return env_vars

    async def list_services(self) -> List[Dict]:
        """List all Cloud Run services"""
        parent = f'projects/{self.config.project_id}/locations/{self.config.region}'

        services = []

        try:
            for service in self.client.list_services(parent=parent):
                services.append({
                    'name': service.name.split('/')[-1],
                    'url': service.uri,
                    'updated': service.update_time,
                    'generation': service.generation
                })
        except Exception as e:
            console.print(f'[yellow]Warning: Could not list services: {e}[/yellow]')

        return services

    async def delete_service(self, service_name: str):
        """Delete a Cloud Run service"""
        service_path = (f'projects/{self.config.project_id}/locations/{self.config.region}/'
                       f'services/{service_name}')

        try:
            console.print(f'[yellow]Deleting service {service_name}...[/yellow]')

            operation = self.client.delete_service(name=service_path)
            operation.result(timeout=300)

            console.print(f'[green]+ Deleted {service_name}[/green]')

        except exceptions.NotFound:
            console.print(f'[yellow]Service not found: {service_name}[/yellow]')
        except Exception as e:
            console.print(f'[red]Error deleting service: {e}[/red]')
            raise

    async def get_service_logs(self, service_name: str, limit: int = 100) -> List[Dict]:
        """Get logs for a service (requires Cloud Logging API)"""
        # This would use Cloud Logging API
        # For now, return placeholder
        console.print(f'[dim]Use: gcloud run services logs read {service_name} --limit={limit}[/dim]')
        return []
