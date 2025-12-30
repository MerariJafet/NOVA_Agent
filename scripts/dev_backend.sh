#!/bin/bash
# scripts/dev_backend.sh

# Exit on error
set -e

echo "🚀 Starting NOVA Backend..."

# Check if venv exists, create if not
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Ensure port 8000 is free (gentle kill)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is occupied. Attempting to free it..."
    fuser -k 8000/tcp || true
    sleep 1
fi

# Start server
echo "✅ Backend starting on http://localhost:8000"
python nova.py start
