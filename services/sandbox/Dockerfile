# syntax=docker/dockerfile:1.4

# Use Ubuntu as base OS
FROM ubuntu:24.04

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
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    gcc \
    redis-server \
    curl

# Set python3.12 as default python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Copy requirements for dependencies
COPY services/sandbox/requirements.txt .

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip,sharing=shared \
    pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application code
COPY ./services/sandbox/src/main.py /app/main.py

# Create WORKSPACE directory and non-root user
RUN useradd -m vuhitra && \
    mkdir -p /app/WORKSPACE /var/lib/redis /var/log/redis && \
    chown -R vuhitra:vuhitra /app /var/lib/redis /var/log/redis

USER vuhitra

# Expose ports (Redis: 6379, App: 8000)
EXPOSE 6379 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start Redis with password authentication and the Flask application
# REDIS_PASSWORD environment variable is required for security
CMD if [ -z "$REDIS_PASSWORD" ]; then \
        echo "ERROR: REDIS_PASSWORD environment variable is required"; \
        exit 1; \
    fi && \
    redis-server --daemonize yes --bind 0.0.0.0 --protected-mode yes --requirepass "$REDIS_PASSWORD" && \
    python main.py
