#!/bin/bash
# FAKTA - Quick Start Script
# Run this to set up and launch the project.

echo "======================================"
echo "  FAKTA - Quick Start"
echo "======================================"

# Step 1: Install dependencies
echo ""
echo "[1/5] Installing dependencies..."
pip install -r requirements.txt

# Step 2: Create data directories
echo ""
echo "[2/5] Creating data directories..."
mkdir -p data/{raw,processed,training,evaluation}
mkdir -p data/evidence
mkdir -p models/lstm
mkdir -p notebooks

# Step 3: Check API key
echo ""
echo "[3/5] Checking API configuration..."
if [ -f .env ]; then
    echo "  .env file found ✓"
else
    echo "  .env file not found. Copy from .env.example:"
    echo "  cp .env.example .env"
    echo "  Then edit .env and add your GEMINI_API_KEY"
fi

# Step 4: Collect data (optional)
echo ""
echo "[4/5] Data collection..."
echo "  Run: python src/data/collect.py"
echo "  Or download datasets manually to data/training/"

# Step 5: Start services
echo ""
echo "[5/5] Ready to start!"
echo ""
echo "  Start API server:"
echo "    python src/api/main.py"
echo ""
echo "  Start demo UI (in new terminal):"
echo "    streamlit run app/streamlit_app.py"
echo ""
echo "  Run fusion engine test:"
echo "    python src/fusion/confidence_fusion.py"
echo ""
echo "  Run preprocessing test:"
echo "    python src/preprocessing/cleaning.py"
echo ""
echo "======================================"
