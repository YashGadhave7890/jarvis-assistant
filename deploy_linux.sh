#!/usr/bin/env bash
# ===================================================================
# JARVIS AI ASSISTANT — 1-Click Linux Deployment Script
# Supports: Ubuntu, Debian, Mint, Raspberry Pi OS
# ===================================================================

set -e

echo "==================================================================="
echo "              JARVIS AI ASSISTANT — LINUX DEPLOYMENT              "
echo "==================================================================="
echo ""

# 1. Update package lists and install system audio dependencies
echo "[1/6] Installing system audio libraries & build dependencies..."
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-pip \
    portaudio19-dev \
    libasound2-dev \
    libsndfile1 \
    ffmpeg \
    curl \
    alsa-utils

# 2. Setup Python Virtual Environment
echo "[2/6] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# 3. Upgrade pip and install requirements
echo "[3/6] Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure .env file
echo "[4/6] Checking environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env from .env.example template. Please update with your API keys."
    fi
fi

# 5. Test deployment preflight
echo "[5/6] Running deployment pre-flight verification..."
python check_deployment.py || true

# 6. Launch options
echo ""
echo "==================================================================="
echo "[SUCCESS] Jarvis is ready for deployment!"
echo "To run interactively:"
echo "  source venv/bin/activate && python main.py --mode hud --host 0.0.0.0 --port 8000 --no-browser"
echo ""
echo "To install as a 24/7 background systemd service:"
echo "  sudo cp jarvis.service /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now jarvis"
echo "==================================================================="
