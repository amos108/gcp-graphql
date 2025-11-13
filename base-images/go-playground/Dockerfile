# Base image for Go microservices
FROM golang:1.21-alpine AS builder

# Install system dependencies
RUN apk add --no-cache git ca-certificates

# Set working directory
WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Build stage is completed in service-specific Dockerfiles

# Runtime stage
FROM alpine:latest

# Install ca-certificates
RUN apk --no-cache add ca-certificates

# Set working directory
WORKDIR /app

# Set environment variables
ENV PORT=8080

# Default command (will be overridden by services)
CMD ["./main"]
