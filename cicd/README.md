# CI/CD System

Automated builds using Google Cloud Build API.

## Features

- ✅ **Automated base image builds** when dependencies change
- ✅ **Service-specific triggers** for individual microservices
- ✅ **Manual trigger execution** for on-demand builds
- ✅ **Pure Python** using Google Cloud Build API (no GitHub Actions needed)

## How It Works

The CI/CD system creates Cloud Build triggers that:

1. Watch for file changes (configurable patterns)
2. Execute `cloudbuild.yaml` when triggered
3. Build and push Docker images to Artifact Registry
4. Optionally deploy to Cloud Run

## Setup

### 1. Set up all triggers

```bash
python -m cicd.cli setup
```

This creates triggers for:
- Python base image
- Node.js base image
- Go base image

### 2. List triggers

```bash
python -m cicd.cli list
```

Output:
```
Build Triggers in globalwinner

build-python-base-image
  ID: abc123...
  Description: Build Python base image when dependencies change
  File: base-images/python-playground/cloudbuild.yaml

build-nodejs-base-image
  ID: def456...
  ...
```

## Usage

### Create triggers for base images

```bash
python -m cicd.cli create-base-images
```

### Create trigger for a service

```bash
python -m cicd.cli create-service payment-service
```

### Run a trigger manually

```bash
# Get trigger ID from 'list' command
python -m cicd.cli run abc123...

# Build from specific branch
python -m cicd.cli run abc123... --branch develop
```

### Delete a trigger

```bash
python -m cicd.cli delete abc123...
```

## Cloud Build Configuration Files

Each base image has a `cloudbuild.yaml`:

```yaml
# base-images/python-playground/cloudbuild.yaml

steps:
  # Build image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '...', '.']

  # Push image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '...']

images:
  - 'us-east1-docker.pkg.dev/globalwinner/base-images/python-playground:latest'

substitutions:
  _REGION: 'us-east1'
  _IMAGE_NAME: 'python-playground'
```

## Trigger Types

### Manual Triggers (Current)

Triggers are created but must be run manually:

```bash
python -m cicd.cli run <trigger-id>
```

### Automatic Triggers (Future)

To enable automatic builds on git push:

1. Connect a Cloud Source Repository or GitHub repo
2. Update triggers to include git event filters
3. Builds run automatically on push

## Architecture

```
File Change
    ↓
Cloud Build Trigger
    ↓
Execute cloudbuild.yaml
    ↓
Build Docker Image
    ↓
Push to Artifact Registry
    ↓
(Optional) Deploy to Cloud Run
```

## Trigger Configuration

Triggers watch for file changes:

```python
BuildConfig(
    name='build-python-base-image',
    description='Build Python base image when dependencies change',
    filename='base-images/python-playground/cloudbuild.yaml',
    included_files=[
        'base-images/python-playground/**',
        'shared/python/playground_sdk/**'
    ]
)
```

When any file in `included_files` changes, the trigger runs.

## Cost

- **Build time**: $0.003/build-minute
- **Storage**: Already covered by Artifact Registry

Example:
- 10 builds/month
- 5 minutes each
- Cost: 10 × 5 × $0.003 = **$0.15/month**

## Advanced: Service-Specific Triggers

Create a `cloudbuild.yaml` in your service:

```yaml
# services/payment-service/cloudbuild.yaml

steps:
  # Build image using buildpacks
  - name: 'gcr.io/k8s-skaffold/pack'
    args:
      - 'build'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/services/payment-service:${SHORT_SHA}'
      - '--builder'
      - 'gcr.io/buildpacks/builder:v1'

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'payment-service'
      - '--image'
      - '${_REGION}-docker.pkg.dev/${PROJECT_ID}/services/payment-service:${SHORT_SHA}'
      - '--region'
      - '${_REGION}'
```

Then create trigger:

```bash
python -m cicd.cli create-service payment-service
```

## Troubleshooting

### Trigger not found

Make sure you're using the correct trigger ID from `list` command.

### Build fails

Check Cloud Build logs:
```bash
# In GCP Console: Cloud Build > History
# Or use gcloud:
gcloud builds list --limit=10
gcloud builds log <build-id>
```

### Permission denied

Make sure Cloud Build service account has permissions:
- Artifact Registry Writer
- Cloud Run Admin (for deployments)

## Integration with Deployment System

The CI/CD system complements the deployment system:

- **CI/CD**: Builds images automatically
- **Deployment CLI**: Deploys services on-demand

You can use both together:
1. CI/CD builds base images when dependencies change
2. Deployment CLI deploys services using those base images

## Next Steps

1. ✅ Set up triggers: `python -m cicd.cli setup`
2. 📦 Build base images (manual trigger or use deploy system)
3. 🚀 Create service-specific triggers as needed
4. 🔄 (Optional) Connect git repository for automatic builds

## API Reference

The `TriggerManager` class provides programmatic access:

```python
from cicd import TriggerManager
from deploy.config import Config

config = Config.load()
manager = TriggerManager(config.project_id, config.region)

# Create triggers
trigger_id = manager.create_base_image_triggers()

# List triggers
triggers = manager.list_triggers()

# Run trigger
build_id = manager.run_trigger(trigger_id)

# Delete trigger
manager.delete_trigger(trigger_id)
```
