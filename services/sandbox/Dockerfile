# syntax=docker/dockerfile:1.4

# Use Ubuntu as base OS
FROM ubuntu:24.04 AS r-packages

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install R and build dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    r-base r-base-dev gcc g++ gfortran \
    libcurl4-openssl-dev libssl-dev libxml2-dev \
    libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
    libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev && \
    rm -rf /var/lib/apt/lists/*

# Install R packages with caching
RUN --mount=type=cache,target=/tmp/downloaded_packages,sharing=shared \
    --mount=type=cache,target=/tmp/R-compile,sharing=shared \
    mkdir -p /usr/local/lib/R/site-library && \
    Rscript -e "options(repos = list(CRAN = 'https://cloud.r-project.org')); \
    dir.create('/tmp/downloaded_packages', showWarnings = FALSE, recursive = TRUE); \
    dir.create('/tmp/R-compile', showWarnings = FALSE, recursive = TRUE); \
    Sys.setenv(R_COMPILE_PKGS = '1'); \
    Sys.setenv(TMPDIR = '/tmp/R-compile'); \
    install.packages(c( \
      'data.table', 'lubridate', 'zoo', \
      'car', 'MASS', 'lmtest', 'sandwich', 'psych', 'boot', \
      'tm', 'textclean', 'stringr', 'tidytext', 'quanteda', \
      'dplyr', 'ggplot2', 'tidyr', 'readr', 'purrr', 'tibble', 'forcats' \
    ), destdir = '/tmp/downloaded_packages', Ncpus = 4)"

# Final stage
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
    python3.12 python3.12-venv python3.12-dev python3-pip curl r-base \
    libcurl4-openssl-dev libssl-dev libxml2-dev \
    libfontconfig1-dev libharfbuzz-dev libfribidi-dev \
    libfreetype6-dev libpng-dev libtiff5-dev libjpeg-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy R packages from the build stage
COPY --from=r-packages /usr/local/lib/R/site-library /usr/local/lib/R/site-library
COPY --from=r-packages /usr/lib/R/site-library /usr/lib/R/site-library

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
