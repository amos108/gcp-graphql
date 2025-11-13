"""Artifact Registry API client for managing container images"""

from google.cloud import artifactregistry_v1
from google.cloud.artifactregistry_v1 import Repository
from google.api_core import exceptions
from rich.console import Console
from typing import List, Dict

from .config import Config

console = Console()


class ArtifactRegistry:
    """Manage container images in Artifact Registry"""

    def __init__(self, config: Config):
        self.config = config
        self.client = artifactregistry_v1.ArtifactRegistryClient()

    async def image_exists(self, image_name: str) -> bool:
        """Check if image exists in registry"""
        # Parse image name: region-docker.pkg.dev/project/repo/image:tag
        parts = image_name.split('/')

        if len(parts) < 3:
            return False

        repository = parts[-2]  # e.g., 'services'
        image_with_tag = parts[-1]  # e.g., 'payment-service:a7b3c9d2'
        image_name_only = image_with_tag.split(':')[0]
        version_tag = image_with_tag.split(':')[1] if ':' in image_with_tag else 'latest'

        try:
            parent = (f'projects/{self.config.project_id}/locations/{self.config.region}/'
                     f'repositories/{repository}')

            # List packages (images)
            packages = self.client.list_packages(parent=parent)

            # Find the specific package
            for package in packages:
                pkg_name = package.name.split('/')[-1]
                if pkg_name == image_name_only:
                    # Check if version exists
                    versions = self.client.list_versions(parent=package.name)
                    for version in versions:
                        version_name = version.name.split('/')[-1]
                        if version_tag in version_name:
                            return True

            return False

        except exceptions.NotFound:
            return False
        except Exception as e:
            console.print(f'[dim]Could not verify image: {e}[/dim]')
            return False

    async def ensure_repository(self, repository_name: str = None):
        """Ensure repository exists, create if not"""
        if repository_name is None:
            repository_name = self.config.artifact_registry

        parent = f'projects/{self.config.project_id}/locations/{self.config.region}'
        repo_path = f'{parent}/repositories/{repository_name}'

        try:
            # Try to get existing repository
            self.client.get_repository(name=repo_path)
            console.print(f'[dim]✓ Repository {repository_name} exists[/dim]')

        except exceptions.NotFound:
            # Create repository
            console.print(f'[cyan]Creating repository {repository_name}...[/cyan]')

            repository = Repository(
                format_=Repository.Format.DOCKER,
                description=f'Container images for {repository_name}'
            )

            operation = self.client.create_repository(
                parent=parent,
                repository_id=repository_name,
                repository=repository
            )

            # Wait for creation to complete
            operation.result(timeout=300)
            console.print(f'[green]✓ Created repository {repository_name}[/green]')

        except Exception as e:
            console.print(f'[red]Error with repository: {e}[/red]')
            raise

    async def list_images(self, repository_name: str = None) -> List[Dict]:
        """List all images in repository"""
        if repository_name is None:
            repository_name = self.config.artifact_registry

        parent = (f'projects/{self.config.project_id}/locations/{self.config.region}/'
                 f'repositories/{repository_name}')

        images = []

        try:
            packages = self.client.list_packages(parent=parent)

            for package in packages:
                package_name = package.name.split('/')[-1]

                # Get versions for this package
                versions = self.client.list_versions(parent=package.name)

                for version in versions:
                    images.append({
                        'name': package_name,
                        'version': version.name.split('/')[-1],
                        'created': version.create_time,
                        'url': f'{self.config.region}-docker.pkg.dev/{self.config.project_id}/{repository_name}/{package_name}'
                    })

        except exceptions.NotFound:
            console.print(f'[yellow]Repository {repository_name} not found[/yellow]')

        return images

    async def delete_image(self, image_name: str, version: str):
        """Delete a specific image version"""
        parent = (f'projects/{self.config.project_id}/locations/{self.config.region}/'
                 f'repositories/{self.config.artifact_registry}/packages/{image_name}')

        version_path = f'{parent}/versions/{version}'

        try:
            operation = self.client.delete_version(name=version_path)
            operation.result(timeout=60)
            console.print(f'[green]✓ Deleted {image_name}:{version}[/green]')

        except exceptions.NotFound:
            console.print(f'[yellow]Version not found: {image_name}:{version}[/yellow]')
        except Exception as e:
            console.print(f'[red]Error deleting image: {e}[/red]')
            raise
