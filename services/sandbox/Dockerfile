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

# Install system dependencies and Python 3.12
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3.12-dev python3-pip curl gosu && \
    rm -rf /var/lib/apt/lists/*

# Set python3.12 as default python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Copy requirements for dependencies
COPY services/sandbox/requirements.txt .

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip,sharing=shared \
    pip install --break-system-packages -r requirements.txt

# Copy and install spaCy large model from local wheel (if exists), otherwise download
COPY services/sandbox/packages/ /tmp/packages/
RUN if [ -f /tmp/packages/en_core_web_lg-3.8.0-py3-none-any.whl ]; then \
        pip install --break-system-packages /tmp/packages/en_core_web_lg-3.8.0-py3-none-any.whl; \
    else \
        pip install --break-system-packages https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl; \
    fi && \
    rm -rf /tmp/packages

# Copy application code
COPY ./services/sandbox/src /app
COPY ./src /app/src

# Copy entrypoint script
COPY ./services/sandbox/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create WORKSPACE directory and non-root user
RUN useradd -m vuhitra && \
    mkdir -p /app/WORKSPACE/mirrors && \
    chown -R vuhitra:vuhitra /app

# Note: We start as root to fix volume permissions, then switch to vuhitra user
# USER vuhitra will be handled by entrypoint script

# Expose port (App: 8000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start the Flask application
CMD ["python", "main.py"]
