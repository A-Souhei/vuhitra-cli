# syntax=docker/dockerfile:1.4

# Use official PostgreSQL image as base
FROM postgres:16-alpine

# Set working directory
WORKDIR /app

# Set environment variables for PostgreSQL
ENV POSTGRES_DB=vuhitra \
    POSTGRES_INITDB_ARGS="--encoding=UTF8 --locale=C" \
    PGDATA=/var/lib/postgresql/data/pgdata

# Install additional PostgreSQL extensions
RUN apk add --no-cache \
    postgresql-contrib \
    postgresql-dev

# Copy initialization scripts
COPY services/postgres/init-scripts/ /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# Health check
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD pg_isready -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-vuhitra} || exit 1

# Use default postgres entrypoint
# The official postgres image handles initialization automatically
