# syntax=docker/dockerfile:1.4

# Use Ubuntu as base OS
FROM ubuntu:24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    REDIS_VERSION=7.4.1

# Set working directory
WORKDIR /app

# Install Redis and dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    redis-server \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create directories and non-root user
RUN useradd -m redis_user && \
    mkdir -p /var/lib/redis /var/log/redis /data && \
    chown -R redis_user:redis_user /var/lib/redis /var/log/redis /data

USER redis_user

# Expose Redis port
EXPOSE 6379

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
    CMD redis-cli -a "${REDIS_PASSWORD}" ping || exit 1

# Start Redis with password authentication
# REDIS_PASSWORD environment variable is required for security
CMD if [ -z "$REDIS_PASSWORD" ]; then \
        echo "ERROR: REDIS_PASSWORD environment variable is required"; \
        exit 1; \
    fi && \
    redis-server \
    --bind 0.0.0.0 \
    --protected-mode yes \
    --requirepass "$REDIS_PASSWORD" \
    --dir /data \
    --appendonly yes \
    --appendfilename "appendonly.aof"
