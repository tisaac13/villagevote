#!/bin/bash
# CivicSwipe Setup Script for Claude Code
# Run this after extracting the project

set -e

echo "🚀 CivicSwipe Setup for Claude Code"
echo "===================================="
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ]; then
    echo "❌ Error: Please run this script from the civicswipe project root"
    exit 1
fi

# Step 1: Python environment
echo "📦 Step 1: Setting up Python environment..."
cd backend

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

cd ..

# Step 2: Environment configuration
echo ""
echo "⚙️  Step 2: Configuring environment..."
if [ ! -f "backend/.env" ]; then
    echo "Creating .env file from template..."
    cp backend/.env.example backend/.env
    echo "⚠️  IMPORTANT: Edit backend/.env and add your API keys"
else
    echo ".env file already exists"
fi

# Step 3: Docker services
echo ""
echo "🐳 Step 3: Starting Docker services..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d postgres redis
    echo "Waiting for PostgreSQL to be ready..."
    sleep 5
else
    echo "⚠️  Docker Compose not found. Please install Docker and run:"
    echo "   docker-compose up -d"
fi

# Step 4: Database setup
echo ""
echo "🗄️  Step 4: Setting up database..."
if command -v psql &> /dev/null; then
    echo "Checking if database exists..."
    if psql -lqt | cut -d \| -f 1 | grep -qw civicswipe; then
        echo "Database 'civicswipe' already exists"
    else
        echo "Creating database..."
        createdb civicswipe
    fi
    
    echo "Running migrations..."
    psql -d civicswipe -f database/001_initial_schema.sql
else
    echo "⚠️  psql not found. Please install PostgreSQL client and run:"
    echo "   createdb civicswipe"
    echo "   psql -d civicswipe -f database/001_initial_schema.sql"
fi

# Step 5: Verification
echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Edit backend/.env and add your API keys:"
echo "   - CONGRESS_API_KEY"
echo "   - OPENSTATES_API_KEY"
echo "   - GOOGLE_MAPS_API_KEY"
echo "   - OPENAI_API_KEY or ANTHROPIC_API_KEY"
echo ""
echo "2. Start the development server:"
echo "   cd backend"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "3. Visit http://localhost:8000/docs for API documentation"
echo ""
echo "4. See docs/IMPLEMENTATION_GUIDE.md for development tasks"
