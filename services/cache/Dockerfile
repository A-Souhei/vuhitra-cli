# syntax=docker/dockerfile:1.4

# Use Ubuntu as base OS
FROM ubuntu:22.04

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VUHITRA_MODE=DEV \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies, Python 3.12, and Redis
RUN --mount=type=cache,target=/var/cache/apt,sharing=shared \
    --mount=type=cache,target=/var/lib/apt,sharing=shared \
    apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    gcc \
    redis-server

# Set python3.12 as default python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip,sharing=shared \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 vuhitra && \
    chown -R vuhitra:vuhitra /app \
    && mkdir -p /var/lib/redis /var/log/redis \
    && chown -R vuhitra:vuhitra /var/lib/redis /var/log/redis

USER vuhitra

# Expose ports (Redis: 6379, App: 8000)
EXPOSE 6379 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD redis-cli ping || exit 1

# Start Redis and the application
CMD redis-server --daemonize yes --bind 0.0.0.0 --protected-mode no && python main.py
