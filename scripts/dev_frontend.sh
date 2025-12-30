#!/bin/bash
# scripts/dev_frontend.sh

# Exit on error
set -e

echo "🚀 Starting NOVA Frontend..."

cd nova-webui

# Install deps if node_modules missing
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start dev server
echo "✅ Frontend starting on http://localhost:5173"
npm run dev
