# syntax=docker/dockerfile:1.4

# Use Ubuntu as base OS
FROM ubuntu:24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    ES_VERSION=8.15.3 \
    ES_HOME=/usr/share/elasticsearch \
    ES_PATH_CONF=/etc/elasticsearch \
    ES_JAVA_HOME=/usr/share/elasticsearch/jdk

# Install dependencies
RUN --mount=type=cache,target=/var/cache/apt,sharing=shared \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=shared \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    wget \
    curl \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Download and install Elasticsearch
RUN --mount=type=cache,target=/root/.cache/downloads,sharing=shared \
    cd /root/.cache/downloads && \
    if [ ! -f elasticsearch-${ES_VERSION}.tar.gz ]; then \
        wget -qO elasticsearch-${ES_VERSION}.tar.gz \
        https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${ES_VERSION}-linux-x86_64.tar.gz && \
        wget -qO elasticsearch-${ES_VERSION}.tar.gz.sha512 \
        https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-${ES_VERSION}-linux-x86_64.tar.gz.sha512; \
    fi && \
    sha512sum -c elasticsearch-${ES_VERSION}.tar.gz.sha512 && \
    mkdir -p ${ES_HOME} && \
    tar -xzf elasticsearch-${ES_VERSION}.tar.gz -C ${ES_HOME} --strip-components=1

# Create directories and set permissions
RUN mkdir -p ${ES_PATH_CONF} \
    /var/lib/elasticsearch \
    /var/log/elasticsearch && \
    groupadd -g 1000 elasticsearch && \
    useradd -u 1000 -g 1000 -s /bin/bash -m elasticsearch && \
    chown -R elasticsearch:elasticsearch \
    ${ES_HOME} \
    ${ES_PATH_CONF} \
    /var/lib/elasticsearch \
    /var/log/elasticsearch

# Copy default configuration
RUN cp ${ES_HOME}/config/* ${ES_PATH_CONF}/ || true

# Set working directory
WORKDIR ${ES_HOME}

USER elasticsearch

# Expose ports (HTTP: 9200, Transport: 9300)
EXPOSE 9200 9300

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:9200/_cluster/health || exit 1

# Start Elasticsearch
CMD ["bin/elasticsearch"]
