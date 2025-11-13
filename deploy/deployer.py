"""Main service deployment orchestrator"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import json
from git import Repo
from google.cloud import storage
from rich.console import Console
from rich.progress import Progress

from .builder import CloudBuilder
from .registry import ArtifactRegistry
from .runner import CloudRunDeployer
from .config import Config

console = Console()


class ServiceDeployer:
    """Deploy microservices using Google Cloud APIs"""

    def __init__(self, config: Config):
        self.config = config
        self.repo_root = Path(__file__).parent.parent
        self.repo = Repo(self.repo_root)

        # Initialize Google Cloud clients
        self.builder = CloudBuilder(config)
        self.registry = ArtifactRegistry(config)
        self.runner = CloudRunDeployer(config)
        self.storage_client = storage.Client(project=config.project_id)

    def get_git_sha(self) -> str:
        """Get current git SHA for versioning"""
        return self.repo.head.commit.hexsha[:8]

    def get_git_user(self) -> str:
        """Get current git user email"""
        try:
            return self.repo.config_reader().get_value("user", "email", default="unknown")
        except:
            return "unknown"

    def has_changes(self, service_name: str, since_sha: str) -> bool:
        """Check if service code changed since last deploy"""
        service_path = f'services/{service_name}'

        try:
            # Get diff between commits for service directory
            old_commit = self.repo.commit(since_sha)
            new_commit = self.repo.head.commit

            diff = old_commit.diff(new_commit, paths=service_path)
            return len(diff) > 0
        except:
            # If error (e.g., commit not found), assume changes
            return True

    def create_git_tag(self, service_name: str, version: str, env: str):
        """Create git tag for deployment"""
        tag_name = f'services/{service_name}@{version}-{env}'

        try:
            # Delete existing tag if exists
            if tag_name in self.repo.tags:
                self.repo.delete_tag(tag_name)

            # Create new tag
            self.repo.create_tag(tag_name, message=f'Deploy {service_name} to {env}')
            console.print(f'[green]✓[/green] Tagged: {tag_name}')
        except Exception as e:
            console.print(f'[dim]Could not create tag: {e}[/dim]')

    def load_service_config(self, service_name: str) -> Dict:
        """Load service configuration"""
        config_file = self.repo_root / 'services' / service_name / 'config.json'

        if config_file.exists():
            return json.loads(config_file.read_text())

        # Default config
        return {
            'memory': '512Mi',
            'cpu': '1',
            'timeout': 60,
            'min_instances': 0,
            'max_instances': 100,
            'allow_unauthenticated': True,
            'env': {}
        }

    def load_deployment_record(self, service_name: str) -> Dict:
        """Load deployment record"""
        deployed_file = self.repo_root / 'services' / service_name / '.deployed'

        if deployed_file.exists():
            return json.loads(deployed_file.read_text())
        return {}

    def save_deployment_record(self, service_name: str, env: str,
                               version: str, image: str, url: str):
        """Save deployment record"""
        deployed_file = self.repo_root / 'services' / service_name / '.deployed'

        data = self.load_deployment_record(service_name)

        data[env] = {
            'version': version,
            'image': image,
            'url': url,
            'deployed_at': datetime.utcnow().isoformat(),
            'deployed_by': self.get_git_user()
        }

        deployed_file.parent.mkdir(parents=True, exist_ok=True)
        deployed_file.write_text(json.dumps(data, indent=2))
        console.print(f'[green]✓[/green] Updated deployment record')

    async def deploy(self, service_name: str, env: str = 'production',
                     force: bool = False):
        """Main deployment function"""
        console.print(f'\n[bold]🎯 Deploying {service_name} to {env}[/bold]')

        # Check if service directory exists
        service_path = self.repo_root / 'services' / service_name
        if not service_path.exists():
            console.print(f'[red]✗ Service not found: {service_name}[/red]')
            console.print(f'[dim]Path checked: {service_path}[/dim]')
            return

        # 1. Get version (git SHA)
        version = self.get_git_sha()
        console.print(f'[cyan]📦 Version:[/cyan] {version}')

        # 2. Check if rebuild needed
        deployment_record = self.load_deployment_record(service_name)

        if env in deployment_record and not force:
            last_version = deployment_record[env]['version']

            if last_version == version:
                console.print(f'[yellow]✓ Already deployed at {version}, skipping...[/yellow]')
                console.print(f'[dim]Use --force to redeploy[/dim]')
                return

            if not self.has_changes(service_name, last_version):
                console.print(f'[yellow]✓ No changes since {last_version}, skipping...[/yellow]')
                console.print(f'[dim]Use --force to redeploy[/dim]')
                return

        # 3. Build image using Cloud Build
        try:
            image_name = await self.builder.build_service(service_name, service_path, version)
        except Exception as e:
            console.print(f'[red]✗ Build failed: {e}[/red]')
            return

        # 4. Deploy to Cloud Run
        try:
            service_config = self.load_service_config(service_name)
            url = await self.runner.deploy_service(
                service_name=service_name,
                image=image_name,
                env=env,
                config=service_config
            )
        except Exception as e:
            console.print(f'[red]✗ Deployment failed: {e}[/red]')
            return

        # 5. Save deployment record
        self.save_deployment_record(service_name, env, version, image_name, url)

        # 6. Create git tag
        self.create_git_tag(service_name, version, env)

        console.print(f'\n[bold green]✅ Successfully deployed {service_name}@{version}[/bold green]')
        console.print(f'[blue]🌐 URL:[/blue] {url}')

        return url

    async def deploy_multiple(self, service_names: List[str],
                             env: str = 'production', parallel: bool = True):
        """Deploy multiple services"""
        import asyncio

        console.print(f'\n[bold]🎯 Deploying {len(service_names)} services[/bold]')

        if parallel:
            # Deploy in parallel
            tasks = [self.deploy(name, env) for name in service_names]
            await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Deploy sequentially
            for name in service_names:
                await self.deploy(name, env)

        console.print('\n[bold green]✅ All deployments complete[/bold green]')

    async def rollback(self, service_name: str, to_version: str,
                      env: str = 'production'):
        """Rollback to a previous version"""
        console.print(f'[yellow]⏪ Rolling back {service_name} to {to_version}...[/yellow]')

        # Get image from version
        image_name = self.config.get_image_url(service_name, to_version)

        # Verify image exists
        if not await self.registry.image_exists(image_name):
            console.print(f'[red]✗ Image not found: {image_name}[/red]')
            console.print('[dim]Available versions:[/dim]')
            images = await self.registry.list_images()
            for img in images:
                if img['name'] == service_name:
                    console.print(f"  - {img['version']}")
            return

        # Deploy old version
        try:
            service_config = self.load_service_config(service_name)
            url = await self.runner.deploy_service(
                service_name=service_name,
                image=image_name,
                env=env,
                config=service_config
            )

            # Update record
            self.save_deployment_record(service_name, env, to_version, image_name, url)

            console.print(f'[green]✓ Rolled back to {to_version}[/green]')

        except Exception as e:
            console.print(f'[red]✗ Rollback failed: {e}[/red]')

    def list_deployments(self, service_name: Optional[str] = None):
        """List deployed services and versions"""
        services_dir = self.repo_root / 'services'

        if not services_dir.exists():
            console.print('[yellow]No services directory found[/yellow]')
            return

        if service_name:
            services = [service_name]
        else:
            services = [
                p.name for p in services_dir.iterdir()
                if p.is_dir() and not p.name.startswith('.')
            ]

        for name in services:
            record = self.load_deployment_record(name)

            if not record:
                continue

            console.print(f'\n[bold]{name}:[/bold]')
            for env, info in record.items():
                console.print(f'  [cyan]{env}:[/cyan] {info["version"]} '
                            f'({info["deployed_at"]})')
                console.print(f'    [blue]URL:[/blue] {info["url"]}')
                console.print(f'    [dim]By: {info["deployed_by"]}[/dim]')
