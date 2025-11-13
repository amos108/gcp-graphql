"""CLI interface for CI/CD trigger management"""

import typer
from rich.console import Console
from rich.table import Table
from pathlib import Path
import sys

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from deploy.config import Config
from .trigger_manager import TriggerManager

app = typer.Typer(help="CI/CD Trigger Management CLI")
console = Console()


def load_config() -> Config:
    """Load deployment configuration"""
    try:
        return Config.load()
    except Exception as e:
        console.print(f'[red]Error loading config: {e}[/red]')
        raise typer.Exit(1)


@app.command()
def setup():
    """Set up all CI/CD triggers"""
    config = load_config()
    manager = TriggerManager(config.project_id, config.region)

    manager.setup_all_triggers()


@app.command()
def list():
    """List all build triggers"""
    config = load_config()
    manager = TriggerManager(config.project_id, config.region)

    triggers = manager.list_triggers()

    if not triggers:
        return

    # Create summary table
    table = Table(title=f"\nSummary ({len(triggers)} triggers)")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="dim")

    for trigger in triggers:
        table.add_row(trigger.name, trigger.description)

    console.print(table)


@app.command()
def create_base_images():
    """Create triggers for base image builds"""
    config = load_config()
    manager = TriggerManager(config.project_id, config.region)

    trigger_ids = manager.create_base_image_triggers()

    console.print(f'\n[green]Created {len(trigger_ids)} triggers[/green]')


@app.command()
def create_service(service_name: str):
    """Create trigger for a specific service"""
    config = load_config()
    manager = TriggerManager(config.project_id, config.region)

    trigger_id = manager.create_service_trigger(service_name)

    console.print(f'\n[green]✓ Created trigger for {service_name}[/green]')
    console.print(f'[dim]  Trigger ID: {trigger_id}[/dim]')


@app.command()
def run(
    trigger_id: str = typer.Argument(..., help='Trigger ID to run'),
    branch: str = typer.Option('main', help='Git branch to build')
):
    """Manually run a trigger"""
    config = load_config()
    manager = TriggerManager(config.project_id, config.region)

    build_id = manager.run_trigger(trigger_id, branch)

    console.print(f'\n[green]✓ Build started: {build_id}[/green]')


@app.command()
def delete(trigger_id: str = typer.Argument(..., help='Trigger ID to delete')):
    """Delete a build trigger"""
    config = load_config()
    manager = TriggerManager(config.project_id, config.region)

    # Confirm deletion
    confirm = typer.confirm(f"Delete trigger {trigger_id}?")
    if not confirm:
        console.print('[yellow]Cancelled[/yellow]')
        return

    manager.delete_trigger(trigger_id)


@app.command()
def info():
    """Show CI/CD configuration"""
    config = load_config()

    console.print('\n[bold]CI/CD Configuration[/bold]\n')
    console.print(f'[cyan]Project ID:[/cyan] {config.project_id}')
    console.print(f'[cyan]Region:[/cyan] {config.region}')
    console.print()


if __name__ == '__main__':
    app()
