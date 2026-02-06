#!/bin/bash
# CivicSwipe Celery Workers Startup Script
# Starts both the Celery worker and beat scheduler

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

cd "$PROJECT_DIR/backend"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo -e "${RED}Error: Virtual environment not found. Run setup.sh first.${NC}"
    exit 1
fi

echo -e "${GREEN}==============================${NC}"
echo -e "${GREEN}  CivicSwipe Celery Workers   ${NC}"
echo -e "${GREEN}==============================${NC}"

# Check if Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo -e "${RED}Error: Redis is not running. Start it with: docker-compose up -d redis${NC}"
    exit 1
fi

echo -e "${GREEN}Redis is connected!${NC}"

# Start both worker and beat in background
echo -e "${YELLOW}Starting Celery worker...${NC}"
celery -A app.tasks.celery_app worker --loglevel=info &
WORKER_PID=$!

echo -e "${YELLOW}Starting Celery beat scheduler...${NC}"
celery -A app.tasks.celery_app beat --loglevel=info &
BEAT_PID=$!

echo ""
echo -e "${GREEN}Celery services started:${NC}"
echo -e "  Worker PID: $WORKER_PID"
echo -e "  Beat PID: $BEAT_PID"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Trap SIGINT to stop both processes
trap "echo 'Stopping Celery services...'; kill $WORKER_PID $BEAT_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for processes
wait
