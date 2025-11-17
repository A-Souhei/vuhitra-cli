# syntax=docker/dockerfile:1.4

# Use Ubuntu as base OS
FROM ubuntu:24.04

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VUHITRA_MODE=DEV \
    DEBIAN_FRONTEND=noninteractive \
    R_LIBS_USER=/usr/local/lib/R/site-library

# Install system dependencies, Python 3.12, R, and exploratory tools
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    # Python and core tools
    python3.12 python3.12-venv python3.12-dev python3-pip \
    # R and R development tools
    r-base r-base-dev \
    # Exploratory and development tools
    tree \
    vim \
    nano \
    less \
    curl \
    wget \
    git \
    jq \
    httpie \
    net-tools \
    iputils-ping \
    dnsutils \
    telnet \
    netcat-openbsd \
    # Build tools for R packages
    build-essential \
    gfortran \
    libxml2-dev \
    libssl-dev \
    libcurl4-openssl-dev \
    libfontconfig1-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libudunits2-dev \
    # PostgreSQL client libraries
    libpq-dev \
    # Compression tools
    zip \
    unzip \
    gzip \
    bzip2 \
    xz-utils \
    # User switching utility
    gosu && \
    rm -rf /var/lib/apt/lists/*

# Set python3.12 as default python
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Copy requirements for dependencies
COPY services/sandbox/requirements.txt .
COPY services/sandbox/install_r_packages.R /tmp/

# Create R library directory with proper permissions before installation
RUN mkdir -p /usr/local/lib/R/site-library && \
    chmod -R 755 /usr/local/lib/R/site-library

# Install Python dependencies with pip cache mount
RUN --mount=type=cache,target=/root/.cache/pip,sharing=shared \
    pip install --break-system-packages -r requirements.txt

# Install R packages with proper cache mount for R's package download location
# R downloads packages to /tmp/R_downloads (cached), builds in /tmp/R_build (cached)
RUN --mount=type=cache,target=/tmp/R_downloads,sharing=shared \
    --mount=type=cache,target=/tmp/R_build,sharing=shared \
    mkdir -p /tmp/R_downloads /tmp/R_build && \
    TMPDIR=/tmp/R_build R -e "options(repos = list(CRAN = 'https://cloud.r-project.org')); install.packages('lintr', destdir='/tmp/R_downloads', quiet = TRUE)" && \
    TMPDIR=/tmp/R_build Rscript /tmp/install_r_packages.R && \
    rm /tmp/install_r_packages.R

# Copy and install spaCy large model from local wheel (if exists), otherwise download
# Use pip cache mount for efficient caching
COPY services/sandbox/packages/ /tmp/packages/
RUN --mount=type=cache,target=/root/.cache/pip,sharing=shared \
    if [ -f /tmp/packages/en_core_web_lg-3.8.0-py3-none-any.whl ]; then \
        pip install --break-system-packages /tmp/packages/en_core_web_lg-3.8.0-py3-none-any.whl; \
    else \
        pip install --break-system-packages https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl; \
    fi && \
    rm -rf /tmp/packages

# Copy application code
COPY ./services/sandbox/src /app
COPY ./src /app/src

# Copy heuristics configuration
COPY ./services/sandbox/heuristics_config.yaml /heuristics_config.yaml

# Copy templates and static files for web UI
COPY ./services/sandbox/templates /app/templates
COPY ./services/sandbox/static /app/static

# Ensure templates and static files have correct permissions
# Set directories to 755 (rwxr-xr-x) and files to 644 (rw-r--r--)
RUN find /app/templates /app/static -type d -exec chmod 755 {} \; && \
    find /app/templates /app/static -type f -exec chmod 644 {} \;

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
