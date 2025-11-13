#!/bin/bash

# Build all base images and push to Artifact Registry

set -e

# Load config
PROJECT_ID=$(grep 'project_id' ../../config.json | cut -d'"' -f4)
REGION=$(grep 'region' ../../config.json | cut -d'"' -f4)

echo "Building base images for project: $PROJECT_ID"
echo "Region: $REGION"

# Build Python base image
echo ""
echo "Building Python base image..."
cd python-playground
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/base-images/python-playground:latest \
  --project ${PROJECT_ID}
cd ..

# Build Node.js base image
echo ""
echo "Building Node.js base image..."
cd nodejs-playground
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/base-images/nodejs-playground:latest \
  --project ${PROJECT_ID}
cd ..

# Build Go base image
echo ""
echo "Building Go base image..."
cd go-playground
gcloud builds submit \
  --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/base-images/go-playground:latest \
  --project ${PROJECT_ID}
cd ..

echo ""
echo "✅ All base images built successfully!"
