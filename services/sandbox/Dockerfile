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
RUN --mount=type=cache,target=/var/cache/apt,sharing=shared \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=shared \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3.12-dev python3-pip gcc g++ curl r-base r-base-dev && \
    rm -rf /var/lib/apt/lists/*



# Install R packages for data analysis
RUN --mount=type=cache,target=/root/.cache/R,sharing=shared \
    Rscript -e "options(repos = list(CRAN = 'https://cloud.r-project.org')); \
    install.packages(c( \
      'tidyverse', 'data.table', 'lubridate', 'zoo', \
      'car', 'MASS', 'lmtest', 'sandwich', 'psych', 'boot', \
      'tm', 'textclean', 'stringr', 'tidytext', 'quanteda' \
    ))"

# Set python3.12 as default python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Copy requirements for dependencies
COPY services/sandbox/requirements.txt .

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip,sharing=shared \
    pip install --no-cache-dir --break-system-packages -r requirements.txt

# Download spaCy English language model
RUN --mount=type=cache,target=/root/.cache/pip,sharing=shared \
    python -m pip install --break-system-packages https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl

# Copy application code
COPY ./services/sandbox/src /app
COPY ./src /app/src

# Create WORKSPACE directory and non-root user
RUN useradd -m vuhitra && \
    mkdir -p /app/WORKSPACE && \
    chown -R vuhitra:vuhitra /app

USER vuhitra

# Expose port (App: 8000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the Flask application
CMD python main.py
