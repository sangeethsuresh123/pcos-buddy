#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "==> Working in: $(pwd)"

if ! python3 -c "import venv, ensurepip" >/dev/null 2>&1; then
  echo "==> Installing python3-venv + python3-pip (needs sudo)..."
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3-venv python3-pip
fi

echo "==> Removing incompatible Windows venv (venv/Scripts is for Windows)..."
[ -d venv ] && rm -rf venv

echo "==> Creating Linux virtualenv..."
python3 -m venv venv

echo "==> Upgrading pip..."
venv/bin/pip install --upgrade pip -q

echo "==> Installing requirements..."
venv/bin/pip install -r requirements.txt

echo "==> Re-indexing vector store (knowledge docs)..."
venv/bin/python setup_vectordb.py

echo "==> Loading trained ML model..."
venv/bin/python -c "from backend.ml.predictor import get_predictor; p=get_predictor(); print('model loaded:', p.is_loaded)"

echo ""
echo "Setup complete. Run the server with:"
echo "    cd ~/projects/chatbot && venv/bin/python -m backend.app"
echo "Then open http://localhost:8000"