FROM python:3.11-slim

WORKDIR /app

# Keep apt cache for faster rebuilds
RUN rm -f /etc/apt/apt.conf.d/docker-clean; \
    echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# Install system dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY services/transformer/requirements.txt .

# Install heavy dependencies in order (with pip cache mount)
# Install torch first (~800MB) - most stable, rarely changes
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps torch==2.1.2

# Install transformers (~400MB) - depends on many packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps transformers==4.36.2

# Install sentence-transformers and keybert
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps sentence-transformers==2.7.0

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-deps keybert==0.8.5

# Install Flask and remaining lightweight dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install flask==2.3.3 flask-cors==4.0.0

# Install any missing dependencies from requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy application code
COPY services/transformer/ .

# Expose port
EXPOSE 5050

# Run the application
CMD ["python", "app.py"]
