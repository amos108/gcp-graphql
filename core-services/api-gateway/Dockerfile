# API Gateway Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy playground SDK
COPY ../../shared/python/playground_sdk ./playground_sdk
RUN pip install -e ./playground_sdk

# Copy application code
COPY src/ ./src/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV GCP_PROJECT=true-ability-399619
ENV GCP_REGION=us-east1

# Expose port
EXPOSE 8080

# Run application
CMD ["python", "-m", "src.main"]
