#!/bin/bash
# CivicSwipe Development Startup Script
# This script starts all services needed for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==============================${NC}"
echo -e "${GREEN}  CivicSwipe Development Mode ${NC}"
echo -e "${GREEN}==============================${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

cd "$PROJECT_DIR"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Start PostgreSQL and Redis
echo -e "${YELLOW}Starting PostgreSQL and Redis...${NC}"
docker-compose up -d postgres redis

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for databases to be ready...${NC}"
sleep 5

# Check if PostgreSQL is ready
until docker-compose exec -T postgres pg_isready -U civicswipe > /dev/null 2>&1; do
    echo "Waiting for PostgreSQL..."
    sleep 2
done
echo -e "${GREEN}PostgreSQL is ready!${NC}"

# Check if Redis is ready
until docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; do
    echo "Waiting for Redis..."
    sleep 2
done
echo -e "${GREEN}Redis is ready!${NC}"

# Activate virtual environment and start backend
cd backend
echo -e "${YELLOW}Starting backend API...${NC}"
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate

    echo -e "${GREEN}Backend starting on http://localhost:8000${NC}"
    echo -e "${GREEN}API docs available at http://localhost:8000/docs${NC}"
    echo ""

    # Start the server
    python main.py
else
    echo -e "${RED}Error: Virtual environment not found. Run setup.sh first.${NC}"
    exit 1
fi
