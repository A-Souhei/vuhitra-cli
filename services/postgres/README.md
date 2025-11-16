# PostgreSQL Service

PostgreSQL database service for the Vuhitra sandbox environment, optimized for data analysis workflows with Python and R.

## 🎯 Features

- **PostgreSQL 16 Alpine**: Lightweight and secure PostgreSQL image
- **Pre-configured Extensions**: UUID, full-text search, hstore, and more
- **Analytics Schema**: Dedicated schema for data analysis workloads
- **Health Checks**: Automatic health monitoring
- **Persistent Storage**: Data persisted in Docker volume

## 📦 Installed Extensions

The database is initialized with the following extensions:

- **uuid-ossp**: UUID generation functions
- **pg_trgm**: Trigram matching for similarity searches
- **hstore**: Key-value pair storage within columns
- **btree_gin**: GIN index support for composite types
- **btree_gist**: GiST index support for composite types

## 🗄️ Database Structure

### Default Database
- **Name**: `vuhitra`
- **User**: `vuhitra` (configurable via environment variables)
- **Schemas**:
  - `public` - Default schema
  - `analytics` - Dedicated schema for data analysis

### Search Path
The database is configured with search path: `public, analytics`

## 🚀 Usage

### Starting the Service

```bash
# Start with the app profile
cd services
docker compose --profile app up -d postgres

# Or start all app services
docker compose --profile app up -d
```

### Connecting from Sandbox

The sandbox service automatically has access to PostgreSQL with the following environment variables:

```bash
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=vuhitra
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=vuhitra
```

### Python Connection Example

```python
import os
import psycopg2
from sqlalchemy import create_engine
import pandas as pd

# Method 1: Using psycopg2 directly
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', 'postgres'),
    port=os.getenv('POSTGRES_PORT', '5432'),
    user=os.getenv('POSTGRES_USER', 'vuhitra'),
    password=os.getenv('POSTGRES_PASSWORD'),
    database=os.getenv('POSTGRES_DB', 'vuhitra')
)

cursor = conn.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())
conn.close()

# Method 2: Using SQLAlchemy (recommended)
db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(db_url)

# Method 3: Using pandas (easiest for data analysis)
df = pd.read_sql_query("SELECT * FROM information_schema.tables", engine)
print(df)

# Write data to database
df.to_sql('my_table', engine, schema='analytics', if_exists='replace', index=False)
```

### R Connection Example

```r
library(DBI)
library(RPostgres)

# Create connection
con <- dbConnect(
  RPostgres::Postgres(),
  host = Sys.getenv("POSTGRES_HOST", "postgres"),
  port = as.integer(Sys.getenv("POSTGRES_PORT", "5432")),
  user = Sys.getenv("POSTGRES_USER", "vuhitra"),
  password = Sys.getenv("POSTGRES_PASSWORD"),
  dbname = Sys.getenv("POSTGRES_DB", "vuhitra")
)

# Query data
result <- dbGetQuery(con, "SELECT version()")
print(result)

# Write data frame to database
dbWriteTable(con, "my_table", mtcars, overwrite = TRUE)

# Read data into a data frame
df <- dbReadTable(con, "my_table")
print(head(df))

# Close connection
dbDisconnect(con)
```

### Direct Connection (from host machine)

```bash
# Using psql client
psql -h localhost -p 15432 -U vuhitra -d vuhitra

# Using connection string
psql "postgresql://vuhitra:your-password@localhost:15432/vuhitra"
```

## 🔧 Configuration

### Environment Variables

Set these in your `.env` file:

```bash
# PostgreSQL credentials
POSTGRES_USER=vuhitra
POSTGRES_PASSWORD=your-secure-postgres-password-here
POSTGRES_DB=vuhitra
```

### Ports

- **Internal**: 5432 (within Docker network)
- **External**: 15432 (accessible from host)

## 📁 Volume Management

### Data Persistence

PostgreSQL data is stored in the `postgres_data` Docker volume:

```bash
# Inspect the volume
docker volume inspect services_postgres_data

# Backup the data
docker run --rm -v services_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data

# Restore the data
docker run --rm -v services_postgres_data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres-backup.tar.gz -C /
```

## 🔍 Monitoring

### Health Check

The service includes automatic health checks:

```bash
# Check service health
docker compose ps postgres

# View logs
docker compose logs postgres

# Follow logs in real-time
docker compose logs -f postgres
```

### Database Status

```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('vuhitra'));

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname IN ('public', 'analytics')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check active connections
SELECT count(*) FROM pg_stat_activity;
```

## 🛠️ Maintenance

### Vacuum and Analyze

```sql
-- Vacuum all tables
VACUUM ANALYZE;

-- Vacuum specific table
VACUUM ANALYZE analytics.my_table;
```

### Reindex

```sql
-- Reindex all tables
REINDEX DATABASE vuhitra;

-- Reindex specific table
REINDEX TABLE analytics.my_table;
```

## 🔒 Security

- Credentials are managed via environment variables
- Database runs in isolated Docker network
- External access requires explicit port mapping (15432)
- User permissions are scoped to vuhitra database

## 📝 Notes

- The PostgreSQL service must be running before the sandbox service starts
- The sandbox service automatically waits for PostgreSQL health check to pass
- Initialization scripts in `/docker-entrypoint-initdb.d/` run only on first startup
- To reinitialize, delete the `postgres_data` volume and restart

## 🐛 Troubleshooting

### Connection Refused

```bash
# Check if service is running
docker compose ps postgres

# Check service logs
docker compose logs postgres

# Verify health status
docker inspect vuhitra-postgres --format='{{.State.Health.Status}}'
```

### Permission Denied

```sql
-- Grant permissions to user
GRANT ALL PRIVILEGES ON SCHEMA analytics TO vuhitra;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO vuhitra;
```

### Reset Database

```bash
# Stop services
docker compose --profile app down

# Remove PostgreSQL volume
docker volume rm services_postgres_data

# Restart services (will reinitialize database)
docker compose --profile app up -d
```
