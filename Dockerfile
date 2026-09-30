# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS base

# Install OS dependencies, git, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast, deterministic dependency resolution
COPY --from=ghcr.io/astral-sh/uv:0.5.15 /uv /bin/uv

WORKDIR /app

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080

# Copy dependency specifications
COPY pyproject.toml uv.lock ./

# Install Python dependencies into virtualenv
RUN uv sync --frozen --no-install-project

# Copy project source code, skills, and configuration
COPY src/ ./src/
COPY skills/ ./skills/
COPY golden_tests/ ./golden_tests/
COPY config.yaml ./

# Install mathlore-forge package into the virtualenv
RUN uv sync --frozen

# Default command starts the web dashboard & webhook server on Cloud Run
EXPOSE 8080
CMD ["mathlore-forge", "serve", "--host", "0.0.0.0", "--port", "8080"]
