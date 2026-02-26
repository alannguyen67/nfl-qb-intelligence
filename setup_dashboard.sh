#!/bin/bash
# ──────────────────────────────────────────────────────────
# NFL QB Intelligence — Dashboard Setup Script
# Run from your project root: bash setup_dashboard.sh
# ──────────────────────────────────────────────────────────

set -e

echo "🏈 Setting up QB Intelligence Dashboard..."
echo ""

# Step 1: Create React app with Vite
echo "📦 Creating React app with Vite..."
npm create vite@latest dashboard -- --template react
cd dashboard

# Step 2: Install dependencies
echo "📥 Installing dependencies..."
npm install

# Step 3: Create data directory
mkdir -p src/data

# Step 4: Go back to project root
cd ..

# Step 5: Export real data from Python pipeline
echo "📊 Exporting QB data from your pipeline..."
PYTHONPATH=. python src/data/export_dashboard_data.py

# Step 6: Check if data was exported
if [ ! -f "dashboard/src/data/qb_data.json" ]; then
    echo "⚠️  Data export failed. Check that data/processed/pass_plays_qualified.parquet exists."
    echo "    Run: PYTHONPATH=. python -m src.data.load_data"
    exit 1
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy the App.jsx file I provided into dashboard/src/App.jsx"
echo "  2. cd dashboard"
echo "  3. npm run dev"
echo "  4. Open http://localhost:5173 in your browser"
echo ""
