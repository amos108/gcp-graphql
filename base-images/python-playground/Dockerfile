# Base image for Python microservices
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install common dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy playground SDK
COPY ../../shared/python/playground_sdk ./playground_sdk
RUN pip install -e ./playground_sdk

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Default command (will be overridden by services)
CMD ["python", "-m", "src.main"]
