# Package Management: Build vs Runtime Installation

## 🎯 Recommended Approach: Hybrid Strategy

### Core Packages → Dockerfile (Build Time)
### User Packages → Volume (Runtime)

---

## 📦 Strategy Breakdown

### 1. **Core Packages in Dockerfile** (Current Approach) ✅

```dockerfile
# Install essential packages at build time
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --break-system-packages -r requirements.txt
```

**What goes here:**
- Required packages for application to run
- Data analysis frameworks (pandas, numpy, scikit-learn)
- Database clients (psycopg2, redis, elasticsearch)
- Testing/linting tools (pytest, ruff, mypy)

**Benefits:**
- ✅ Reproducible across all containers
- ✅ Version-locked in requirements.txt
- ✅ Cached via BuildKit (fast rebuilds)
- ✅ Immutable - what you build is what you deploy

---

### 2. **User Packages via Virtual Environment** (Recommended)

Instead of volumes for system package directories, create user-specific virtual environments:

#### Python: User Virtual Environments

```dockerfile
# In Dockerfile - create venv directory
RUN mkdir -p /app/WORKSPACE/.venvs && \
    chown -R vuhitra:vuhitra /app/WORKSPACE/.venvs
```

```yaml
# In docker-compose.yml - persist user venvs
volumes:
  - workspace:/app/WORKSPACE  # Already exists, includes .venvs
```

**User workflow:**
```bash
# Inside container
cd /app/WORKSPACE/my_project

# Create project-specific venv
python -m venv .venvs/my_project
source .venvs/my_project/bin/activate

# Install additional packages
pip install experimental-package==1.0.0

# These packages:
# ✅ Persist across container restarts (in volume)
# ✅ Don't affect system packages
# ✅ Are isolated per project
# ❌ Are lost if volume is deleted
```

#### R: User Library Directory

```dockerfile
# In Dockerfile - create user R library
RUN mkdir -p /app/WORKSPACE/.R/library && \
    chown -R vuhitra:vuhitra /app/WORKSPACE/.R
```

```bash
# Inside container - set user library
export R_LIBS_USER=/app/WORKSPACE/.R/library

# Install user packages
R -e "install.packages('experimental_package')"

# These packages:
# ✅ Persist in workspace volume
# ✅ Don't affect system R packages
# ✅ Can be version-controlled via renv
```

---

## 🚫 Why NOT to Volume System Directories

### ❌ Bad: Volume System Package Directories

```yaml
# DON'T DO THIS
volumes:
  - python_packages:/usr/local/lib/python3.12/site-packages
  - r_packages:/usr/local/lib/R/site-library
```

### Problems:

#### 1. **Image Build is Wasted**
```bash
# Build time: 15 minutes installing packages to image
docker build ...

# Runtime: Volume completely overrides installed packages
docker run -v python_packages:/usr/local/lib/python3.12/site-packages

# Result: 15 minutes wasted, packages from image not used
```

#### 2. **Inconsistent Environments**
```bash
# Container 1
docker run sandbox
> pip list  # Shows: pandas==2.0.0

# Container 2 (shares same volume)
docker run sandbox
# User installs: pip install pandas==2.1.0
> pip list  # Shows: pandas==2.1.0

# Container 1 (restart)
docker run sandbox
> pip list  # Now shows: pandas==2.1.0 😱
# Surprise! Your environment changed
```

#### 3. **Permission Chaos**
```
/usr/local/lib/python3.12/site-packages/
├── pandas/           (owner: root)     # Installed during build
├── numpy/            (owner: root)     # Installed during build
├── mypackage/        (owner: vuhitra) # Installed at runtime
└── experimental/     (owner: vuhitra) # Installed at runtime
```

**Issues:**
- Some packages can't be imported due to permissions
- `pip uninstall` fails for root-owned packages
- Mixing ownership is asking for trouble

#### 4. **No Rollback**
```bash
# User accidentally breaks environment
pip install incompatible-package
# Now what?

# With Dockerfile approach:
docker restart  # Environment is fresh again
```

---

## ✅ Recommended Setup

### Update Dockerfile

```dockerfile
# Create user package directories in WORKSPACE
RUN mkdir -p /app/WORKSPACE/.venvs \
             /app/WORKSPACE/.R/library \
             /app/WORKSPACE/.jupyter && \
    chown -R vuhitra:vuhitra /app/WORKSPACE
```

### Update docker-compose.yml

```yaml
sandbox:
  volumes:
    - workspace:/app/WORKSPACE  # Already exists
    # This includes:
    # - User data
    # - User-installed packages (.venvs, .R/library)
    # - Jupyter notebooks
    # - Analysis scripts
```

### Usage Instructions for Users

Create `/app/WORKSPACE/README.md` in the container:

```markdown
# Installing Additional Packages

## Python

### Option 1: Project Virtual Environment (Recommended)
cd /app/WORKSPACE/my_project
python -m venv .venv
source .venv/bin/activate
pip install my-package

### Option 2: User Directory
pip install --user my-package
# Installed to: ~/.local/lib/python3.12/site-packages

## R

### Option 1: Using renv (Recommended)
R -e "install.packages('renv')"
R -e "renv::init()"
R -e "install.packages('my_package')"

### Option 2: User Library
export R_LIBS_USER=/app/WORKSPACE/.R/library
R -e "install.packages('my_package')"

## Jupyter

jupyter notebook --ip=0.0.0.0 --notebook-dir=/app/WORKSPACE
# Notebooks persist in workspace volume
```

---

## 📊 Comparison Table

| Aspect | System Volume | User Venv/Library | Dockerfile Only |
|--------|---------------|-------------------|-----------------|
| **Reproducibility** | ❌ Poor | ⚠️ Medium | ✅ Excellent |
| **Performance** | ⚠️ Medium | ✅ Good | ✅ Good (with cache) |
| **Flexibility** | ✅ High | ✅ High | ❌ Low |
| **Complexity** | ❌ High | ⚠️ Medium | ✅ Low |
| **Permission Issues** | ❌ Frequent | ✅ Rare | ✅ None |
| **Version Control** | ❌ Impossible | ⚠️ Possible (renv) | ✅ Built-in |
| **Image Size** | ❌ Wasted | ✅ Optimized | ✅ Optimized |
| **Container Portability** | ❌ Poor | ⚠️ Medium | ✅ Excellent |

---

## 🎯 Final Recommendation

### **DO:**
1. ✅ Install core packages in Dockerfile
2. ✅ Use BuildKit cache mounts for fast rebuilds
3. ✅ Provide user directories for experimental packages
4. ✅ Document how users can install additional packages
5. ✅ Use workspace volume for user data and venvs

### **DON'T:**
1. ❌ Volume system package directories
2. ❌ Mix system and user package installations
3. ❌ Sacrifice reproducibility for convenience

### **Implementation:**

Current setup is already good! Just add user package directory creation:

```dockerfile
# Add after WORKSPACE creation
RUN mkdir -p /app/WORKSPACE/.venvs \
             /app/WORKSPACE/.R/library && \
    chown -R vuhitra:vuhitra /app/WORKSPACE
```

This gives users:
- ✅ Core packages ready to use (from image)
- ✅ Ability to install experimental packages (in workspace)
- ✅ Persistence of user packages (via workspace volume)
- ✅ No conflicts between system and user packages
- ✅ Reproducible base environment

---

## 🔧 Migration Path

If you want to try the volume approach despite the warnings:

```yaml
# docker-compose.yml
volumes:
  python_user_packages:
    driver: local
  r_user_packages:
    driver: local

sandbox:
  volumes:
    - workspace:/app/WORKSPACE
    - python_user_packages:/home/vuhitra/.local/lib/python3.12/site-packages
    - r_user_packages:/home/vuhitra/R/library
```

**Notes:**
- This uses USER libraries, not system
- Doesn't conflict with system packages
- Still less clean than venv approach

---

*Recommendation: Stick with current Dockerfile approach + user venvs*
