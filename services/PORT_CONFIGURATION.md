# Port Configuration Guide

All service ports in the vuhitra-cli project are now configurable through environment variables in the `.env` file.

## Default Port Mappings

All ports follow the pattern `HOST_PORT:CONTAINER_PORT`:

| Service | Host Port | Container Port | Environment Variables |
|---------|-----------|----------------|----------------------|
| PostgreSQL | 15432 | 5432 | `POSTGRES_HOST_PORT`, `POSTGRES_CONTAINER_PORT` |
| Redis | 16379 | 6379 | `REDIS_HOST_PORT`, `REDIS_CONTAINER_PORT` |
| Sandbox API | 18001 | 8000 | `SANDBOX_HOST_PORT`, `SANDBOX_CONTAINER_PORT` |
| Transformer | 16050 | 5050 | `TRANSFORMER_HOST_PORT`, `TRANSFORMER_CONTAINER_PORT` |
| Elasticsearch HTTP | 9200 | 9200 | `ELASTICSEARCH_HTTP_HOST_PORT`, `ELASTICSEARCH_HTTP_CONTAINER_PORT` |
| Elasticsearch Transport | 9300 | 9300 | `ELASTICSEARCH_TRANSPORT_HOST_PORT`, `ELASTICSEARCH_TRANSPORT_CONTAINER_PORT` |
| Kibana | 5601 | 5601 | `KIBANA_HOST_PORT`, `KIBANA_CONTAINER_PORT` |
| Spark Master | 7077 | 7077 | `SPARK_MASTER_HOST_PORT`, `SPARK_MASTER_CONTAINER_PORT` |
| Spark Master Web UI | 8081 | 8081 | `SPARK_MASTER_WEBUI_HOST_PORT`, `SPARK_MASTER_WEBUI_CONTAINER_PORT` |
| Ollama | 11434 | 11434 | `OLLAMA_HOST_PORT`, `OLLAMA_CONTAINER_PORT` |

## Configuration Files

### Main Configuration: `config.yaml`

The main application configuration should reference the **host ports** (the ports you access from your local machine):

```yaml
redis:
  host: localhost
  port: 16379  # REDIS_HOST_PORT

transformer:
  host: localhost
  port: 16050  # TRANSFORMER_HOST_PORT

postgres:
  host: localhost
  port: 15432  # POSTGRES_HOST_PORT

elasticsearch:
  host: localhost
  port: 9200  # ELASTICSEARCH_HTTP_HOST_PORT
```

### Docker Environment: `services/.env`

The `.env` file contains all port mappings and credentials:

```bash
# Port Mappings
REDIS_HOST_PORT=16379
REDIS_CONTAINER_PORT=6379

TRANSFORMER_HOST_PORT=16050
TRANSFORMER_CONTAINER_PORT=5050

POSTGRES_HOST_PORT=15432
POSTGRES_CONTAINER_PORT=5432

# ... etc
```

## Customizing Ports

To change a service's port:

1. **Edit `services/.env`**: Change the `*_HOST_PORT` value
   ```bash
   REDIS_HOST_PORT=26379  # Custom port
   ```

2. **Update `config.yaml`**: Match the host port
   ```yaml
   redis:
     port: 26379  # Must match REDIS_HOST_PORT
   ```

3. **Restart the service**:
   ```bash
   cd services
   docker-compose restart redis
   ```

## Important Notes

- **Host Ports**: Used by your local machine to connect to services
- **Container Ports**: Internal Docker network ports (usually don't need to change)
- **PostgreSQL**: Bound to `127.0.0.1` only for security
- **All defaults** have fallback values in `docker-compose.yml` using `${VAR:-default}` syntax

## Verifying Configuration

Check if ports are correctly exposed:

```bash
# List running containers with ports
docker ps --format "table {{.Names}}\t{{.Ports}}"

# Test specific service
curl http://localhost:16050/health  # Transformer
redis-cli -p 16379 ping            # Redis
```

## Troubleshooting

### Port Already in Use

If you get "port already allocated" error:

1. Check what's using the port:
   ```bash
   lsof -i :16379  # Check specific port
   ```

2. Either:
   - Stop the conflicting service
   - Or change the port in `.env` and `config.yaml`

### Connection Refused

If services can't connect:

1. Verify `.env` ports match `config.yaml`
2. Check service is running: `docker ps`
3. Check service logs: `docker logs vuhitra-redis`
4. Verify host vs container ports are correct
