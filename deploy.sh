#!/bin/bash

# cPanel Deployment Script for ABA
# This script sets up the application on GoDaddy cPanel hosting

set -e

echo "Starting deployment..."

# Configuration
APP_DIR="$HOME/aba"
PYTHON_VERSION="3.11"

# Navigate to application directory
cd "$APP_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python${PYTHON_VERSION} -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing Python dependencies..."
pip install -e .

# Create necessary directories
echo "Creating application directories..."
mkdir -p tmp
mkdir -p logs

# Set up environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cat > .env << 'EOL'
# OpenRouter API Key - REQUIRED
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Application settings
ABA_HOME=$HOME/.aba
PORT=8000

# Production mode
PRODUCTION=true
EOL
    echo "WARNING: Please edit .env and add your OPENROUTER_API_KEY"
fi

# Create passenger_wsgi.py if it doesn't exist
if [ ! -f "passenger_wsgi.py" ]; then
    echo "Creating passenger_wsgi.py..."
    cp passenger_wsgi.py.template passenger_wsgi.py
fi

# Create tmp/restart.txt to restart Passenger
echo "Restarting application..."
mkdir -p tmp
touch tmp/restart.txt

echo "Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your OPENROUTER_API_KEY"
echo "2. Configure cPanel to point to this directory"
echo "3. Set Python version to ${PYTHON_VERSION} in cPanel Python selector"
echo "4. Ensure passenger_wsgi.py is the entry point"
echo ""
echo "Application should be accessible at https://singularsys.com/aba"
