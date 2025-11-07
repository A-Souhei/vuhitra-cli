# Secrets Management

This project uses `secrets.yaml` to store sensitive configuration like passwords and API keys.

## Setup

### 1. Create secrets.yaml

Copy the template file:
```bash
cp secrets.yaml.template secrets.yaml
```

Edit `secrets.yaml` and update with your actual secrets:
```yaml
redis:
  password: "your-secure-password-here"
```

**IMPORTANT**: `secrets.yaml` is gitignored and should **NEVER** be committed to version control.

### 2. Setup Docker Compose Environment

For running the sandbox service with docker-compose:

```bash
cd services
cp .env.example .env
```

Edit `services/.env` and set your Redis password:
```bash
REDIS_PASSWORD=your-secure-password-here
```

**IMPORTANT**: `services/.env` is gitignored and should **NEVER** be committed.

### 3. Generate a Secure Password

Use one of these methods to generate a secure password:

```bash
# OpenSSL
openssl rand -base64 32

# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# pwgen
pwgen -s 32 1
```

## Running the Sandbox Service

```bash
cd services
export REDIS_PASSWORD=your-secure-password-here  # Or use .env file
docker compose up -d
```

Docker Compose will automatically load `.env` file if it exists.

## For CI/CD

In GitHub Actions or other CI/CD systems, set secrets as environment variables:
- `REDIS_PASSWORD`: Redis authentication password

The application will automatically use environment variables if available, falling back to `secrets.yaml` for local development.

## For Production

Use a proper secrets management system like:
- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets
- Environment variables from secure sources

Never store production secrets in plain text files.

## Troubleshooting

### Error: "REDIS_PASSWORD environment variable is required"

This means the Redis password is not set. You need to either:

1. Set it as an environment variable:
   ```bash
   export REDIS_PASSWORD=your-password
   ```

2. Create `services/.env` file with the password:
   ```bash
   echo "REDIS_PASSWORD=your-password" > services/.env
   ```

3. Pass it when running docker-compose:
   ```bash
   REDIS_PASSWORD=your-password docker compose up
   ```
