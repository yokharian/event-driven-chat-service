# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the frontend project files
COPY src/frontend/pyproject.toml src/frontend/uv.lock ./

# Install dependencies using uv
RUN uv sync --frozen --no-cache

# Copy the rest of the application code
COPY src/commons/ /app/commons/
COPY src/frontend/ /app/src/frontend/

# Expose the port the app runs on
EXPOSE 8501

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV IS_DOCKERIZED=true

# Command to run the application
CMD ["/app/.venv/bin/streamlit", "run", "src/frontend/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
