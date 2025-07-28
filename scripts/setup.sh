#!/usr/bin/env bash
# Codex-compatible Python env setup script

set -e

# support optional plugin installation with `--plugins`
INSTALL_PLUGINS=false
if [[ "$1" == "--plugins" ]]; then
  INSTALL_PLUGINS=true
fi

echo "[*] Creating virtual environment..."
python -m venv .venv
source .venv/bin/activate

echo "[*] Installing core dependencies..."
pip install --upgrade pip
pip install -r requirements-core.txt
if [ "$INSTALL_PLUGINS" = true ]; then
  echo "[*] Installing plugin dependencies..."
  pip install -r requirements-plugins.txt
fi

if [ ! -f .env ]; then
  echo "[*] Creating .env from example..."
  cp .env.example .env
  echo "[!] Customize .env before running production jobs."
fi

echo "[*] Running test suite..."
pytest || echo "[!] Tests require valid .env keys or mocks."

echo "[*] Environment ready. Activate with: source .venv/bin/activate"
