# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (incl. AWS CLI v1 from apt)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    awscli \
    zip \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Prepare project environment with uv (uses rest_api deps for infra tooling)
COPY src/rest_api/pyproject.toml src/rest_api/uv.lock ./
RUN uv venv /app/.venv
RUN uv sync --frozen --no-cache --python /app/.venv/bin/python --project pyproject.toml
# Install AWS SAM CLI via pip (works for amd64/arm64)
RUN uv pip install --python /app/.venv/bin/python aws-sam-cli

# Copy the application code and Makefile for SAM build hooks
COPY src/ /app/src/

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV SAM_CLI_TELEMETRY=0

# Set localstack env vars
ENV AWS_ACCESS_KEY_ID=test
ENV AWS_SECRET_ACCESS_KEY=test
ENV AWS_ENDPOINT_URL=http://localhost:4566
ENV AWS_DEFAULT_REGION=us-east-1

# Set cloudformation parameters
ENV STACK_NAME=chat-service-stack
ENV ENVIRONMENT=local
ENV STATE_TABLE_NAME=simplechat_connections
ENV EVENT_BUS_TABLE_NAME=chat_events
ENV DEPLOYMENT_BUCKET=chat-service-sam-deploy

ENV SOURCE_TEMPLATE_FILE=/app/src/infra/template-dev.yaml

WORKDIR /app/src

# Ensure deploy script is executable and use it as the default entrypoint
RUN chmod +x /app/src/infra/sam_deploy.sh
CMD ["/bin/sh", "-c", "set -euo pipefail; TEMPLATE_FILE=.aws-sam/build/template.yaml /app/src/infra/sam_deploy.sh" ]


