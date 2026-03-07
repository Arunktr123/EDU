#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# SUPERNATURAL — Render Build Script
# Called automatically during each deploy
# ═══════════════════════════════════════════════════════════════
set -o errexit   # exit on error

echo "🔧 Installing Python dependencies..."
cd backend
pip install --upgrade pip
pip install -r requirements.txt

echo "📁 Verifying frontend assets..."
cd ..
if [ -d "frontend/static" ] && [ -d "frontend/templates" ]; then
    echo "✅ Frontend assets found"
else
    echo "❌ Frontend directory missing!"
    exit 1
fi

echo "✅ Build complete!"

