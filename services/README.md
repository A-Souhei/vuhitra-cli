# Vuhitra Services

This directory contains Docker Compose configurations for the Vuhitra project services.

## Services

### Main Services (docker-compose.yml)
- **Redis**: In-memory data store with persistence
- **Sandbox**: Python execution environment with data science libraries
- **Elasticsearch**: Search and analytics engine
- **Kibana**: Web UI for Elasticsearch

### Optional Services (Profiles)

#### Spark (docker-compose.yml with `--profile spark`)
- **Spark Master**: Apache Spark cluster master node
- **Spark Worker**: Apache Spark worker node

#### Ollama (docker-compose.yml with `--profile ollama`)
- **Ollama**: Local LLM inference server with lightweight model
- **Ollama Setup**: One-time model initialization container

## Usage

### Running Core Services Only

For CI/CD or when Spark is not needed:

```bash
docker compose up -d
```

### Running with Spark Services

When you need Spark services:

```bash
# Start core services + Spark
docker compose --profile spark up -d
```

### Running with Ollama (Local LLM)

When you need local LLM inference (works on both CPU and GPU):

```bash
# Start core services + Ollama
docker compose --profile ollama up -d
```

**Ollama Features:**
- Uses **tinyllama** model (~1GB, very lightweight)
- Works on CPU (no GPU required)
- Optional GPU acceleration (uncomment in docker-compose.yml)
- Automatic model download on first start
- Accessible at `http://localhost:11434`

**To enable GPU support:**
1. Ensure NVIDIA Container Toolkit is installed
2. Uncomment the `deploy` section under `ollama` service in docker-compose.yml

**Testing Ollama:**
```bash
# After starting the service
curl http://localhost:11434/api/generate -d '{
  "model": "tinyllama",
  "prompt": "Hello, how are you?"
}'
```

### Running Multiple Profiles

You can combine profiles:

```bash
# Start core services + Spark + Ollama
docker compose --profile spark --profile ollama up -d
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

Optional (for Ollama):
- `OLLAMA_HOST`: Ollama API endpoint (default: `http://ollama:11434`)
- `OLLAMA_MODEL`: Model to use (default: `tinyllama`)
