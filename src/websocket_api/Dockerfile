# Dockerfile for WebSocket API local development server
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy websocket_api pyproject.toml and lock file to root for uv
COPY src/websocket_api/pyproject.toml src/websocket_api/uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-cache

# Copy project structure
COPY src/websocket_api/ /app/websocket_api/
COPY src/commons/ /app/commons/

# Set environment variables
ENV TABLE_NAME=simplechat_connections
ENV AWS_REGION=us-east-1
ENV DYNAMODB_ENDPOINT_URL=http://localstack:4566
ENV WS_PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose WebSocket server port
EXPOSE 8080

# Run uvicorn directly using the uv-created virtual environment
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "websocket_api.local_server:app", "--host", "0.0.0.0", "--port", "8080"]
