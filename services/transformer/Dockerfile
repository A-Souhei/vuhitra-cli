FROM python:3.11-slim

WORKDIR /app

# Keep apt cache for faster rebuilds
RUN rm -f /etc/apt/apt.conf.d/docker-clean; \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# Install system dependencies with cache mount
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY services/transformer/requirements-base.txt .
COPY services/transformer/requirements.txt .

# Install base dependencies first (numpy with version constraint)
# This layer is separate to avoid invalidating torch cache when numpy constraints change
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-cache-dir -r requirements-base.txt

# Install heavy dependencies in a single layer with cache mount
# The pip cache mount ensures torch (~800MB) and transformers (~400MB) are cached between builds
# Using --no-cache-dir with mount cache is more efficient than pip's internal cache
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-cache-dir \
    torch==2.1.2 \
    transformers==4.36.2 \
    sentence-transformers==2.7.0

# Install remaining dependencies (lighter packages)
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    pip install --no-cache-dir \
    flask==2.3.3 \
    flask-cors==4.0.0 \
    keybert==0.8.5 \
    sentry-sdk==1.40.6 \
    protobuf>=3.20.0

# Create cache directory for transformers models
# This allows models to be cached across rebuilds when using volume mounts
RUN mkdir -p /root/.cache/huggingface

# Copy application code
COPY services/transformer/ .

# Expose port
EXPOSE 5050

# Run the application
CMD ["python", "app.py"]
