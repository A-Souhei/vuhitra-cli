# Vuhitra Services

This directory contains Docker Compose configurations for the Vuhitra project services.

## Services

### Main Services (docker-compose.yml)
- **Redis**: In-memory data store with persistence
- **Sandbox**: Python execution environment with data science libraries
- **Elasticsearch**: Search and analytics engine

### Optional Services (docker-compose.spark.yml)
- **Spark Master**: Apache Spark cluster master node
- **Spark Worker**: Apache Spark worker node

## Usage

### Running Core Services Only

For CI/CD or when Spark is not needed:

```bash
docker compose up -d
```

### Running All Services (Including Spark)

When you need Spark services (requires authentication for private image):

```bash
# Authenticate with GitHub Container Registry first
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Start all services
docker compose -f docker-compose.yml -f docker-compose.spark.yml up -d
```

### Managing Services

```bash
# Stop all services
docker compose -f docker-compose.yml -f docker-compose.spark.yml down

# View logs
docker compose -f docker-compose.yml -f docker-compose.spark.yml logs -f

# Rebuild specific service
docker compose build redis
```

## Network Configuration

Both compose files use the shared `vuhitra-network` bridge network, allowing services to communicate across compose files.

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
- `REDIS_PASSWORD`: Secure password for Redis authentication

Optional (for Spark):
- `SPARK_MODE`, `SPARK_MASTER_URL`, etc. (see `.env.example`)
