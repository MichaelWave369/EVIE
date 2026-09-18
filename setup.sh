#!/usr/bin/env bash
# ============================================================
# EVIE v4.0 — First-Time Setup Script
# Run this ONCE to install everything.
# Usage: bash setup.sh
# ============================================================
set -e

echo "🔥 EVIE v4.0 Setup Starting..."
echo ""

# Check Python
python3 --version || { echo "❌ Python 3 not found. Install Python 3.10+ first."; exit 1; }

# Install dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt

# Create .env from example if not exists
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: A .env file was created from .env.example"
    echo "   Edit .env and add your API key before running EVIE!"
    echo "   → Open .env in any text editor and set:"
    echo "     EV_OPENAI_API_KEY=sk-your-key-here"
    echo ""
else
    echo "✅ .env file already exists"
fi

# Create required directories
mkdir -p data/artifacts data/vault_files data/indexes data/sandboxes data/agent_memory data/gumroad

# Initialize the database
echo "🗄️  Initializing database..."
python3 -c "from app.db.migrate import main; main()" && echo "✅ Database initialized"

echo ""
echo "✅ Setup complete!"
echo ""
echo "NEXT STEPS:"
echo "1. Edit .env and add your API key"
echo "2. Run the API server:  bash start_api.sh"
echo "3. Run the dashboard:   bash start_dashboard.sh"
echo "4. Open browser:        http://localhost:8501"
echo ""
