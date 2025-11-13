"""Configuration management for deployment system"""

from pydantic import BaseModel, Field
from pathlib import Path
from typing import Optional, Dict
import json


class Config(BaseModel):
    """Deployment configuration"""

    project_id: str = Field(..., description="GCP Project ID")
    region: str = Field(default='us-central1', description="GCP Region")
    artifact_registry: str = Field(default='services', description="Artifact Registry repository name")
    environments: Optional[Dict[str, Dict]] = Field(default=None, description="Environment configurations")

    @classmethod
    def from_file(cls, config_path: Path) -> 'Config':
        """Load config from JSON file"""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        data = json.loads(config_path.read_text())
        return cls(**data)

    @classmethod
    def from_env(cls) -> 'Config':
        """Load config from environment variables"""
        import os

        project_id = os.getenv('GCP_PROJECT_ID')
        if not project_id:
            raise ValueError("GCP_PROJECT_ID environment variable not set")

        return cls(
            project_id=project_id,
            region=os.getenv('GCP_REGION', 'us-central1'),
            artifact_registry=os.getenv('ARTIFACT_REGISTRY', 'services')
        )

    @classmethod
    def load(cls) -> 'Config':
        """Load config from file or environment (file takes precedence)"""
        # Try to load from config.json in project root
        project_root = Path(__file__).parent.parent
        config_file = project_root / 'config.json'

        if config_file.exists():
            return cls.from_file(config_file)
        else:
            return cls.from_env()

    def get_image_url(self, service_name: str, version: str) -> str:
        """Get full image URL for a service"""
        return (f'{self.region}-docker.pkg.dev/'
                f'{self.project_id}/{self.artifact_registry}/{service_name}:{version}')

    def get_service_url(self, service_name: str, env: str = 'production') -> str:
        """Get Cloud Run service URL"""
        # This will be populated after deployment
        # For now, return placeholder
        return f'https://{service_name}-{self.region.replace("_", "-")}-{self.project_id}.run.app'
