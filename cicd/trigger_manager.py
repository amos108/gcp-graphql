"""Cloud Build Trigger Manager using Google Cloud APIs"""

from google.cloud import cloudbuild_v1
from google.cloud.devtools.cloudbuild_v1 import (
    BuildTrigger,
    GitFileSource,
    RepoSource,
    Build,
    BuildStep
)
from google.api_core import exceptions
from rich.console import Console
from typing import List, Dict, Optional
from pathlib import Path
from pydantic import BaseModel

console = Console()


class BuildConfig(BaseModel):
    """Configuration for a build trigger"""
    name: str
    description: str
    filename: str  # Path to cloudbuild.yaml
    included_files: List[str]  # Files that trigger this build
    substitutions: Dict[str, str] = {}


class TriggerManager:
    """
    Manage Cloud Build triggers using Google Cloud API.

    Creates automated builds for:
    - Base images when base-images/ or shared/python/ changes
    - Core services when core-services/ changes
    - Auto-deploy on specific branches
    """

    def __init__(self, project_id: str, region: str):
        self.project_id = project_id
        self.region = region
        self.client = cloudbuild_v1.CloudBuildClient()
        self.parent = f"projects/{project_id}/locations/{region}"

    def create_trigger(self, config: BuildConfig) -> str:
        """
        Create a Cloud Build trigger.

        Args:
            config: Build configuration

        Returns:
            Trigger ID
        """
        console.print(f'[cyan]Creating trigger: {config.name}...[/cyan]')

        # Check if trigger already exists
        existing = self._get_trigger_by_name(config.name)
        if existing:
            console.print(f'[yellow]Trigger {config.name} already exists, updating...[/yellow]')
            return self._update_trigger(existing.id, config)

        # Create trigger configuration
        trigger = BuildTrigger(
            name=config.name,
            description=config.description,
            filename=config.filename,
            included_files=config.included_files,
            substitutions=config.substitutions,
            # Manual trigger only (no automatic git triggers for now)
            # Can be extended to support GitHub/Cloud Source Repositories
        )

        try:
            created_trigger = self.client.create_build_trigger(
                parent=self.parent,
                build_trigger=trigger
            )

            console.print(f'[green]✓ Created trigger: {config.name}[/green]')
            console.print(f'[dim]  ID: {created_trigger.id}[/dim]')

            return created_trigger.id

        except Exception as e:
            console.print(f'[red]✗ Failed to create trigger: {e}[/red]')
            raise

    def create_base_image_triggers(self) -> List[str]:
        """
        Create triggers for base image builds.

        Returns:
            List of trigger IDs
        """
        console.print('\n[bold]Setting up base image build triggers[/bold]\n')

        triggers = []

        # Python base image trigger
        python_config = BuildConfig(
            name='build-python-base-image',
            description='Build Python base image when dependencies change',
            filename='base-images/python-playground/cloudbuild.yaml',
            included_files=[
                'base-images/python-playground/**',
                'shared/python/playground_sdk/**'
            ],
            substitutions={
                '_REGION': self.region,
                '_IMAGE_NAME': 'python-playground'
            }
        )
        triggers.append(self.create_trigger(python_config))

        # Node.js base image trigger
        nodejs_config = BuildConfig(
            name='build-nodejs-base-image',
            description='Build Node.js base image when dependencies change',
            filename='base-images/nodejs-playground/cloudbuild.yaml',
            included_files=[
                'base-images/nodejs-playground/**',
                'shared/nodejs/**'
            ],
            substitutions={
                '_REGION': self.region,
                '_IMAGE_NAME': 'nodejs-playground'
            }
        )
        triggers.append(self.create_trigger(nodejs_config))

        # Go base image trigger
        go_config = BuildConfig(
            name='build-go-base-image',
            description='Build Go base image when dependencies change',
            filename='base-images/go-playground/cloudbuild.yaml',
            included_files=[
                'base-images/go-playground/**',
                'shared/go/**'
            ],
            substitutions={
                '_REGION': self.region,
                '_IMAGE_NAME': 'go-playground'
            }
        )
        triggers.append(self.create_trigger(go_config))

        console.print(f'\n[green]✓ Created {len(triggers)} base image triggers[/green]')
        return triggers

    def create_service_trigger(self, service_name: str) -> str:
        """
        Create trigger for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            Trigger ID
        """
        config = BuildConfig(
            name=f'deploy-{service_name}',
            description=f'Build and deploy {service_name} on changes',
            filename=f'services/{service_name}/cloudbuild.yaml',
            included_files=[
                f'services/{service_name}/**'
            ],
            substitutions={
                '_REGION': self.region,
                '_SERVICE_NAME': service_name
            }
        )

        return self.create_trigger(config)

    def list_triggers(self) -> List[BuildTrigger]:
        """
        List all build triggers.

        Returns:
            List of triggers
        """
        console.print(f'\n[bold]Build Triggers in {self.project_id}[/bold]\n')

        try:
            triggers = list(self.client.list_build_triggers(parent=self.parent))

            if not triggers:
                console.print('[yellow]No triggers found[/yellow]')
                return []

            for trigger in triggers:
                console.print(f'[cyan]{trigger.name}[/cyan]')
                console.print(f'  ID: {trigger.id}')
                console.print(f'  Description: {trigger.description}')
                console.print(f'  File: {trigger.filename}')
                console.print()

            return triggers

        except Exception as e:
            console.print(f'[red]Error listing triggers: {e}[/red]')
            return []

    def delete_trigger(self, trigger_id: str):
        """
        Delete a build trigger.

        Args:
            trigger_id: ID of trigger to delete
        """
        trigger_name = f"{self.parent}/triggers/{trigger_id}"

        try:
            self.client.delete_build_trigger(name=trigger_name)
            console.print(f'[green]✓ Deleted trigger: {trigger_id}[/green]')

        except exceptions.NotFound:
            console.print(f'[yellow]Trigger not found: {trigger_id}[/yellow]')
        except Exception as e:
            console.print(f'[red]Error deleting trigger: {e}[/red]')
            raise

    def run_trigger(self, trigger_id: str, branch: str = 'main') -> str:
        """
        Manually run a trigger.

        Args:
            trigger_id: ID of trigger to run
            branch: Git branch to build

        Returns:
            Build ID
        """
        console.print(f'[cyan]Running trigger: {trigger_id}...[/cyan]')

        trigger_name = f"{self.parent}/triggers/{trigger_id}"

        try:
            # Create repo source for manual run
            repo_source = RepoSource(
                project_id=self.project_id,
                branch_name=branch
            )

            operation = self.client.run_build_trigger(
                name=trigger_name,
                source=repo_source
            )

            build = operation.metadata.build
            console.print(f'[green]✓ Build started: {build.id}[/green]')
            console.print(f'[dim]  Log URL: {build.log_url}[/dim]')

            return build.id

        except Exception as e:
            console.print(f'[red]Error running trigger: {e}[/red]')
            raise

    def _get_trigger_by_name(self, name: str) -> Optional[BuildTrigger]:
        """Get trigger by name"""
        try:
            triggers = list(self.client.list_build_triggers(parent=self.parent))
            for trigger in triggers:
                if trigger.name == name:
                    return trigger
            return None
        except:
            return None

    def _update_trigger(self, trigger_id: str, config: BuildConfig) -> str:
        """Update existing trigger"""
        trigger_name = f"{self.parent}/triggers/{trigger_id}"

        trigger = BuildTrigger(
            id=trigger_id,
            name=config.name,
            description=config.description,
            filename=config.filename,
            included_files=config.included_files,
            substitutions=config.substitutions
        )

        try:
            updated = self.client.update_build_trigger(
                build_trigger=trigger
            )
            console.print(f'[green]✓ Updated trigger: {config.name}[/green]')
            return updated.id

        except Exception as e:
            console.print(f'[red]Error updating trigger: {e}[/red]')
            raise

    def setup_all_triggers(self):
        """Set up all CI/CD triggers"""
        console.print('\n[bold]🚀 Setting up CI/CD triggers[/bold]\n')

        # Create base image triggers
        self.create_base_image_triggers()

        console.print('\n[green]✅ CI/CD setup complete![/green]')
        console.print('\n[dim]Triggers are manual-run only.[/dim]')
        console.print('[dim]To enable automatic builds, connect a Git repository.[/dim]')
