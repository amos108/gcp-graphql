"""Cloud Build API client for building container images"""

from pathlib import Path
from typing import Optional
from google.cloud import cloudbuild_v1
from google.cloud.devtools.cloudbuild_v1 import Build, BuildStep, Source, StorageSource
from google.cloud import storage
from google.api_core import exceptions
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import tarfile
import io
import time

from .config import Config
from .registry import ArtifactRegistry

console = Console()


class CloudBuilder:
    """Build container images using Cloud Build API"""

    def __init__(self, config: Config):
        self.config = config
        self.client = cloudbuild_v1.CloudBuildClient()
        self.storage_client = storage.Client(project=config.project_id)
        self.registry = ArtifactRegistry(config)

    async def build_service(self, service_name: str, service_path: Path,
                           version: str) -> str:
        """Build service using Cloud Build with buildpacks"""

        image_name = self.config.get_image_url(service_name, version)

        console.print(f'[cyan]🔨 Building {service_name}@{version}...[/cyan]')

        # Ensure artifact registry repository exists
        await self.registry.ensure_repository()

        # Source bucket name
        source_bucket = f'{self.config.project_id}_cloudbuild'
        source_object = f'source/{service_name}-{version}.tar.gz'

        # Upload source to GCS
        await self._upload_source(service_path, source_bucket, source_object)

        # Create build configuration
        build = Build()

        # Source location
        build.source = Source(
            storage_source=StorageSource(
                bucket=source_bucket,
                object_=source_object
            )
        )

        # Use buildpacks for automatic detection (no Dockerfile needed!)
        build.steps = [
            BuildStep(
                name='gcr.io/k8s-skaffold/pack',
                args=[
                    'build',
                    image_name,
                    '--builder', 'gcr.io/buildpacks/builder:v1',
                    '--path', '.',
                    '--cache-image', f'{image_name}-cache'
                ]
            )
        ]

        # Output images
        build.images = [image_name]

        # Build options for better performance
        build.options = cloudbuild_v1.BuildOptions(
            logging=cloudbuild_v1.BuildOptions.LoggingMode.GCS_ONLY,
            machine_type=cloudbuild_v1.BuildOptions.MachineType.E2_HIGHCPU_8
        )

        # Submit build
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task(f"Building {service_name}...", total=None)

            try:
                operation = self.client.create_build(
                    project_id=self.config.project_id,
                    build=build
                )

                # Wait for build to complete (with timeout)
                result = operation.result(timeout=600)  # 10 min timeout

            except Exception as e:
                console.print(f'[red]✗ Build failed: {e}[/red]')
                raise

        # Check build status
        if result.status == Build.Status.SUCCESS:
            console.print(f'[green]✓ Built {image_name}[/green]')
            return image_name
        else:
            error_msg = result.failure_info.detail if result.failure_info else 'Unknown error'
            console.print(f'[red]✗ Build failed: {error_msg}[/red]')

            # Try to get logs
            if result.log_url:
                console.print(f'[dim]Logs: {result.log_url}[/dim]')

            raise Exception(f'Build failed: {error_msg}')

    async def _upload_source(self, source_path: Path, bucket_name: str,
                            object_name: str):
        """Upload source code to Cloud Storage"""

        console.print(f'[dim]Uploading source...[/dim]')

        # Get or create bucket
        try:
            bucket = self.storage_client.get_bucket(bucket_name)
        except exceptions.NotFound:
            # Create bucket with same location as compute region
            bucket = self.storage_client.create_bucket(
                bucket_name,
                location=self.config.region
            )
            console.print(f'[dim]Created bucket: {bucket_name}[/dim]')

        # Create tar.gz of source code
        tar_buffer = io.BytesIO()

        with tarfile.open(fileobj=tar_buffer, mode='w:gz') as tar:
            # Add all files in source directory
            tar.add(source_path, arcname='.')

        # Upload to GCS
        blob = bucket.blob(object_name)
        tar_buffer.seek(0)
        blob.upload_from_file(tar_buffer, content_type='application/gzip')

        console.print(f'[dim]✓ Uploaded source ({len(tar_buffer.getvalue()) // 1024} KB)[/dim]')

    def get_build_logs(self, build_id: str) -> str:
        """Get logs for a specific build"""
        build = self.client.get_build(
            project_id=self.config.project_id,
            id=build_id
        )

        if build.log_url:
            return build.log_url
        else:
            return "No logs available"
