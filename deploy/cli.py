"""CLI interface for service deployment"""

import asyncio
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from typing import List, Optional

from .deployer import ServiceDeployer
from .config import Config

app = typer.Typer(help="GCP Microservices Playground Deployment CLI")
console = Console()


def load_config() -> Config:
    """Load deployment configuration"""
    try:
        return Config.load()
    except Exception as e:
        console.print(f'[red]Error loading config: {e}[/red]')
        console.print('[yellow]Make sure config.json exists or GCP_PROJECT_ID is set[/yellow]')
        raise typer.Exit(1)


@app.command()
def deploy(
    service: str = typer.Argument(..., help='Service name to deploy'),
    env: str = typer.Option('production', '--env', '-e', help='Environment (production/staging/dev)'),
    force: bool = typer.Option(False, '--force', '-f', help='Force rebuild even if no changes')
):
    """Deploy a service to Cloud Run"""
    config = load_config()
    deployer = ServiceDeployer(config)

    asyncio.run(deployer.deploy(service, env, force))


@app.command()
def deploy_all(
    services: List[str] = typer.Argument(..., help='Services to deploy'),
    env: str = typer.Option('production', '--env', '-e', help='Environment'),
    parallel: bool = typer.Option(True, '--parallel/--sequential', help='Deploy in parallel')
):
    """Deploy multiple services"""
    config = load_config()
    deployer = ServiceDeployer(config)

    asyncio.run(deployer.deploy_multiple(services, env, parallel))


@app.command()
def rollback(
    service: str = typer.Argument(..., help='Service name'),
    version: str = typer.Argument(..., help='Version (git SHA) to rollback to'),
    env: str = typer.Option('production', '--env', '-e', help='Environment')
):
    """Rollback service to previous version"""
    config = load_config()
    deployer = ServiceDeployer(config)

    asyncio.run(deployer.rollback(service, version, env))


@app.command()
def list(
    service: Optional[str] = typer.Argument(None, help='Specific service (optional)')
):
    """List deployed services and versions"""
    config = load_config()
    deployer = ServiceDeployer(config)

    deployer.list_deployments(service)


@app.command()
def status():
    """Show deployment status for all services"""
    config = load_config()
    deployer = ServiceDeployer(config)

    # Create table
    table = Table(title="Service Deployment Status")
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Production", style="green")
    table.add_column("Staging", style="yellow")
    table.add_column("Dev", style="blue")

    services_dir = Path(__file__).parent.parent / 'services'

    if not services_dir.exists():
        console.print('[yellow]No services directory found[/yellow]')
        return

    for service_path in sorted(services_dir.iterdir()):
        if not service_path.is_dir() or service_path.name.startswith('.'):
            continue

        record = deployer.load_deployment_record(service_path.name)

        prod_version = record.get('production', {}).get('version', '-')
        staging_version = record.get('staging', {}).get('version', '-')
        dev_version = record.get('dev', {}).get('version', '-')

        table.add_row(service_path.name, prod_version, staging_version, dev_version)

    console.print(table)


@app.command()
def services():
    """List all available Cloud Run services"""
    config = load_config()
    deployer = ServiceDeployer(config)

    console.print(f'\n[bold]Cloud Run Services in {config.project_id}[/bold]\n')

    services_list = asyncio.run(deployer.runner.list_services())

    if not services_list:
        console.print('[yellow]No services found[/yellow]')
        return

    table = Table()
    table.add_column("Service", style="cyan")
    table.add_column("URL", style="blue")
    table.add_column("Updated", style="dim")

    for svc in services_list:
        table.add_row(
            svc['name'],
            svc['url'],
            str(svc['updated']) if svc['updated'] else '-'
        )

    console.print(table)


@app.command()
def images(
    service: Optional[str] = typer.Argument(None, help='Filter by service name')
):
    """List container images in Artifact Registry"""
    config = load_config()
    deployer = ServiceDeployer(config)

    console.print(f'\n[bold]Container Images in {config.artifact_registry}[/bold]\n')

    images_list = asyncio.run(deployer.registry.list_images())

    if not images_list:
        console.print('[yellow]No images found[/yellow]')
        return

    # Filter by service if specified
    if service:
        images_list = [img for img in images_list if img['name'] == service]

    table = Table()
    table.add_column("Service", style="cyan")
    table.add_column("Version", style="green")
    table.add_column("Created", style="dim")

    for img in sorted(images_list, key=lambda x: (x['name'], x['created']), reverse=True):
        table.add_row(
            img['name'],
            img['version'],
            str(img['created']) if img['created'] else '-'
        )

    console.print(table)


@app.command()
def info():
    """Show configuration information"""
    config = load_config()

    console.print('\n[bold]Configuration[/bold]\n')
    console.print(f'[cyan]Project ID:[/cyan] {config.project_id}')
    console.print(f'[cyan]Region:[/cyan] {config.region}')
    console.print(f'[cyan]Artifact Registry:[/cyan] {config.artifact_registry}')
    console.print()


if __name__ == '__main__':
    app()
