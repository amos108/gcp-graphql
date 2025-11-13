"""
Service Creator - Create new microservices from templates

Usage:
    python tools/create_service.py my-service --lang python --description "My cool service"
"""

import typer
import shutil
from pathlib import Path
from rich.console import Console
from typing import Optional

app = typer.Typer(help="Create new microservices from templates")
console = Console()


def replace_placeholders(file_path: Path, replacements: dict):
    """Replace placeholders in a file"""
    if file_path.suffix in ['.py', '.js', '.go', '.md', '.json', '.yaml', '.yml', '.txt', '.sh']:
        try:
            content = file_path.read_text(encoding='utf-8')

            for placeholder, value in replacements.items():
                content = content.replace(f'{{{{{placeholder}}}}}', value)

            file_path.write_text(content, encoding='utf-8')
        except Exception as e:
            console.print(f'[yellow]Warning: Could not process {file_path}: {e}[/yellow]')


def create_service(
    service_name: str,
    language: str,
    description: str,
    output_dir: Path
):
    """Create a new service from template"""

    # Get template directory
    template_dir = Path(__file__).parent / 'templates' / language

    if not template_dir.exists():
        console.print(f'[red]Template not found: {language}[/red]')
        console.print(f'[dim]Available: python, nodejs, go[/dim]')
        raise typer.Exit(1)

    # Create service directory
    service_dir = output_dir / service_name

    if service_dir.exists():
        console.print(f'[red]Service directory already exists: {service_dir}[/red]')
        overwrite = typer.confirm("Overwrite?")
        if not overwrite:
            raise typer.Exit(0)
        shutil.rmtree(service_dir)

    # Copy template
    console.print(f'[cyan]Creating {service_name} from {language} template...[/cyan]')
    shutil.copytree(template_dir, service_dir)

    # Replacements
    replacements = {
        'SERVICE_NAME': service_name,
        'SERVICE_DESCRIPTION': description
    }

    # Replace placeholders in all files
    for file_path in service_dir.rglob('*'):
        if file_path.is_file():
            replace_placeholders(file_path, replacements)

    console.print(f'[green]✓ Created {service_name}[/green]')
    console.print(f'[dim]  Location: {service_dir}[/dim]')

    return service_dir


@app.command()
def create(
    service_name: str = typer.Argument(..., help="Service name (e.g., payment-service)"),
    lang: str = typer.Option('python', '--lang', '-l', help="Language (python, nodejs, go)"),
    description: str = typer.Option("A microservice", '--description', '-d', help="Service description"),
    output: Optional[Path] = typer.Option(None, '--output', '-o', help="Output directory (default: services/)")
):
    """Create a new microservice from template"""

    # Default output directory
    if output is None:
        output = Path(__file__).parent.parent / 'services'

    output.mkdir(parents=True, exist_ok=True)

    # Create service
    service_dir = create_service(service_name, lang, description, output)

    # Print next steps
    console.print('\n[bold]Next steps:[/bold]')
    console.print(f'  1. cd {service_dir.relative_to(Path.cwd())}')
    console.print(f'  2. Edit src/handlers.py (Python) or src/index.js (Node.js)')
    console.print(f'  3. Test locally: python -m src.main')
    console.print(f'  4. Deploy: python -m deploy.cli deploy {service_name}')
    console.print()


@app.command()
def list_templates():
    """List available service templates"""
    templates_dir = Path(__file__).parent / 'templates'

    console.print('\n[bold]Available Templates:[/bold]\n')

    for template in templates_dir.iterdir():
        if template.is_dir():
            console.print(f'  [cyan]{template.name}[/cyan]')

            # Read description from template files if available
            readme = template / 'README.md'
            if readme.exists():
                lines = readme.read_text().split('\n')
                if len(lines) > 2:
                    console.print(f'    [dim]{lines[2]}[/dim]')

    console.print()


if __name__ == '__main__':
    app()
