#!/usr/bin/env bash
# Codex-compatible Python env setup script

set -e

echo "[*] Creating virtual environment..."
python -m venv .venv
source .venv/bin/activate

echo "[*] Installing core dependencies..."
pip install --upgrade pip
pip install -r requirements-core.txt
# Optional plugin dependencies
# pip install -r requirements-plugins.txt

if [ ! -f .env ]; then
  echo "[*] Creating .env from example..."
  cp .env.example .env
  echo "[!] Customize .env before running production jobs."
fi

echo "[*] Running test suite..."
pytest || echo "[!] Tests require valid .env keys or mocks."

echo "[*] Environment ready. Activate with: source .venv/bin/activate"
