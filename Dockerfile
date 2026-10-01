# syntax=docker/dockerfile:1

# Stage 1: Build the mlg compiler binary from the official Mathlingua repository
FROM rust:1.85-slim-bookworm AS mlg-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/mathlingua/mathlingua.git /mathlingua-src
WORKDIR /mathlingua-src
RUN cargo build --release && cp target/release/mlg /usr/local/bin/mlg

# Stage 2: Runtime image
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

# Copy pre-compiled mlg compiler binary from builder stage
COPY --from=mlg-builder /usr/local/bin/mlg /usr/local/bin/mlg

WORKDIR /app

# Set environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080

# Copy dependency specifications
COPY pyproject.toml uv.lock README.md ./

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
