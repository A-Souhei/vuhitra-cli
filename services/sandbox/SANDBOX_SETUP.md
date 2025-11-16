# Sandbox Environment Setup

This document describes the comprehensive data analysis sandbox environment with Python and R support.

## 🎯 Features

### Exploratory Tools
- **File System**: `tree`, `ls`, `file`
- **Text Editors**: `vim`, `nano`, `less`
- **Version Control**: `git`
- **Network Tools**: `curl`, `wget`, `httpie`, `ping`, `netcat`, `telnet`, `dig`
- **Data Processing**: `jq` (JSON), `grep`, regex support
- **Compression**: `zip`, `unzip`, `gzip`, `bzip2`, `xz`

### Programming Languages

#### Python 3.12
- Full Python 3.12 environment
- Virtual environment support (`python3.12-venv`)
- Development headers for building packages

#### R
- R base and development tools
- Full CRAN package support
- Spatial data analysis capabilities

## 📦 Installed Packages

### Python Libraries

#### Data Analysis & Manipulation
- `pandas` - Data manipulation and analysis
- `numpy` - Numerical computing
- `scipy` - Scientific computing
- `openpyxl` - Excel file support
- `xlrd` - Legacy Excel file support

#### Visualization
- `matplotlib` - 2D plotting
- `seaborn` - Statistical data visualization
- `plotly` - Interactive plots
- `bokeh` - Interactive visualizations

#### Machine Learning
- `scikit-learn` - Machine learning algorithms
- `statsmodels` - Statistical modeling

#### Natural Language Processing
- `spacy` - Advanced NLP (with en_core_web_lg model)
- `nltk` - Natural language toolkit
- `vaderSentiment` - Sentiment analysis
- `rapidfuzz` - Fast string matching

#### Database & Storage
- `redis` - Redis client
- `elasticsearch` - Elasticsearch client
- `SQLAlchemy` - SQL toolkit and ORM
- `psycopg2-binary` - PostgreSQL adapter

#### Development Tools & Linters
- `pylint` - Code analysis
- `flake8` - Style guide enforcement
- `black` - Code formatter
- `mypy` - Static type checker
- `isort` - Import sorter
- `autopep8` - Auto-formatter

#### Interactive Development
- `jupyter` - Jupyter notebooks
- `ipykernel` - IPython kernel
- `ipywidgets` - Interactive widgets

#### Utilities
- `requests` - HTTP library
- `python-dateutil` - Date utilities
- `pytz` - Timezone support
- `tqdm` - Progress bars

### R Packages

#### Environment & Dependencies
- `renv` - R environment management

#### Data Manipulation
- `tidyverse` - Collection of R packages for data science
- `lubridate` - Date-time manipulation
- `tidyr` - Data tidying
- `readr` - Fast CSV reading
- `dplyr` - Data manipulation
- `tibble` - Modern data frames
- `glue` - String interpolation
- `here` - Project-relative paths
- `zoo` - Time series

#### Database Access
- `DBI` - Database interface
- `RPostgres` - PostgreSQL interface

#### Visualization
- `ggplot2` - Data visualization
- `reshape`, `reshape2` - Data restructuring
- `gridExtra` - Grid graphics
- `plotly` - Interactive plots
- `ggrepel` - Label placement
- `ggeasy` - Easy ggplot2 theming
- `ggtext` - Rich text in ggplot2

#### Spatial Data
- `sp` - Spatial data classes
- `sf` - Simple features
- `units` - Measurement units
- `leaflet` - Interactive maps

#### Web Applications
- `shiny` - Web application framework
- `shinyWidgets` - Custom widgets
- `shinydashboard` - Dashboard framework

#### Development Tools
- `lintr` - R code linter
- `rlang` - Low-level R programming

## 🚀 Build Optimization

### Cache Mounts
The Dockerfile uses BuildKit cache mounts to speed up rebuilds:

1. **APT Cache** (`/var/cache/apt`): System package downloads
2. **APT Lists** (`/var/lib/apt/lists`): Package metadata
3. **Pip Cache** (`/root/.cache/pip`): Python package downloads
4. **R Package Cache** (`/tmp/downloaded_packages`): R package downloads

### Benefits
- **Faster Rebuilds**: Packages are cached between builds
- **Reduced Bandwidth**: Packages aren't re-downloaded unnecessarily
- **Shared Caches**: Multiple builds can share the same cache

### Building the Image

```bash
# Build with BuildKit (required for cache mounts)
DOCKER_BUILDKIT=1 docker build -t vuhitra-sandbox -f services/sandbox/Dockerfile .

# Or use docker-compose (BuildKit enabled by default in recent versions)
docker-compose build sandbox
```

## 📁 Volume Recommendations

For persistent package storage across container restarts:

```yaml
volumes:
  # Python packages (if using venv inside container)
  - python_venv:/app/venv

  # R packages
  - r_packages:/usr/local/lib/R/site-library

  # Workspace for user data
  - workspace:/app/WORKSPACE

  # Jupyter notebooks
  - jupyter_data:/app/.jupyter
```

## 🔧 Usage Examples

### Python
```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Load and analyze data
df = pd.read_csv('data.csv')
df.describe()
```

### R
```r
library(tidyverse)
library(ggplot2)

# Load and visualize data
data <- read_csv('data.csv')
ggplot(data, aes(x=column1, y=column2)) + geom_point()
```

### PostgreSQL Connection

The sandbox has direct access to a PostgreSQL database for data analysis:

#### Python with SQLAlchemy
```python
import os
from sqlalchemy import create_engine
import pandas as pd

# Create database connection
db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
engine = create_engine(db_url)

# Read data from database
df = pd.read_sql_query("SELECT * FROM my_table", engine)

# Write data to database
df.to_sql('my_table', engine, schema='analytics', if_exists='replace', index=False)
```

#### R with DBI/RPostgres
```r
library(DBI)
library(RPostgres)

# Create connection
con <- dbConnect(
  RPostgres::Postgres(),
  host = Sys.getenv("POSTGRES_HOST"),
  port = as.integer(Sys.getenv("POSTGRES_PORT")),
  user = Sys.getenv("POSTGRES_USER"),
  password = Sys.getenv("POSTGRES_PASSWORD"),
  dbname = Sys.getenv("POSTGRES_DB")
)

# Query data
df <- dbReadTable(con, "my_table")

# Write data
dbWriteTable(con, "my_table", mtcars, overwrite = TRUE)

# Close connection
dbDisconnect(con)
```

### Linting
```bash
# Python
pylint script.py
flake8 script.py
black script.py

# R
Rscript -e "lintr::lint('script.R')"
```

## 🌐 Network Tools

```bash
# Test API endpoints
curl https://api.example.com/data
httpie GET https://api.example.com/data

# Process JSON
curl https://api.example.com/data | jq '.results[]'

# Network diagnostics
ping example.com
dig example.com
telnet example.com 80
```

## 🔒 Security

- Runs as non-root user `vuhitra`
- Minimal base image (Ubuntu 24.04)
- Only necessary packages installed
- Regular security updates recommended

## 📝 Notes

- The virtual environment is available via `python3.12 -m venv`
- R library path: `/usr/local/lib/R/site-library`
- Workspace directory: `/app/WORKSPACE`
- All Python packages installed with `--break-system-packages` flag for system-wide access
