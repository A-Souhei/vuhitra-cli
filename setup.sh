#!/bin/bash

# Setup script for vuhitra-cli
# Initializes configuration files, starts services, and runs tests

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  vuhitra-cli Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Copy secrets.yaml.template to secrets.yaml
echo -e "${BLUE}[1/4] Setting up secrets.yaml...${NC}"
if [ -f "secrets.yaml" ]; then
    echo -e "${YELLOW}  ⚠ secrets.yaml already exists, skipping copy${NC}"
else
    cp secrets.yaml.template secrets.yaml
    echo -e "${GREEN}  ✓ Created secrets.yaml from template${NC}"
fi
echo ""

# Step 2: Copy services/.env.example to services/.env
echo -e "${BLUE}[2/4] Setting up services/.env...${NC}"
if [ -f "services/.env" ]; then
    echo -e "${YELLOW}  ⚠ services/.env already exists, skipping copy${NC}"
else
    cp services/.env.example services/.env
    echo -e "${GREEN}  ✓ Created services/.env from example${NC}"
fi
echo ""

# Step 3: Run docker-compose
echo -e "${BLUE}[3/4] Starting Docker services...${NC}"
cd services
docker-compose up -d
cd ..
echo -e "${GREEN}  ✓ Docker services started${NC}"
echo ""

# Step 4: Run tests
echo -e "${BLUE}[4/4] Running tests...${NC}"
./run_tests.sh

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Setup completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
