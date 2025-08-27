#!/usr/bin/env bash
# FundRunner environment setup script with agentic workflow support

set -e

# Parse arguments
INSTALL_PLUGINS=false
SETUP_CHROMA=false
SKIP_TESTS=false

for arg in "$@"; do
  case $arg in
    --plugins)
      INSTALL_PLUGINS=true
      shift
      ;;
    --chroma)
      SETUP_CHROMA=true
      shift
      ;;
    --skip-tests)
      SKIP_TESTS=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--plugins] [--chroma] [--skip-tests]"
      echo "  --plugins    Install optional plugin dependencies (ML, OpenBB, etc.)"
      echo "  --chroma     Set up ChromaDB server (requires Docker)"
      echo "  --skip-tests Skip running the test suite"
      exit 0
      ;;
  esac
done

echo "[*] Creating virtual environment..."
python -m venv .venv
source .venv/bin/activate

echo "[*] Installing core dependencies..."
pip install --upgrade pip
pip install -r requirements-core.txt

if [ "$INSTALL_PLUGINS" = true ]; then
  echo "[*] Installing plugin dependencies (this may take a while)..."
  pip install -r requirements-plugins.txt
fi

if [ ! -f .env ]; then
  echo "[*] Creating .env from example..."
  cp .env.example .env
  echo "[!] Customize .env with your API keys before running."
  echo "[!] Ensure SIMULATION_MODE=true for safe development."
fi

# Create necessary directories
echo "[*] Creating directory structure..."
mkdir -p artifacts/{strategies,review,xrepo}
mkdir -p docs/{agents,standards,knowledge}
mkdir -p benchmarks

if [ "$SETUP_CHROMA" = true ]; then
  echo "[*] Setting up ChromaDB server..."
  if command -v docker &> /dev/null; then
    echo "[*] Starting ChromaDB with Docker..."
    docker run -d --name chroma-db -p 8000:8000 chromadb/chroma:latest
    echo "[*] ChromaDB server should be running on http://localhost:8000"
    echo "[*] You can also run ChromaDB locally with: chroma run --path ./chroma_data"
  else
    echo "[!] Docker not found. To run ChromaDB locally:"
    echo "    pip install chromadb"
    echo "    chroma run --path ./chroma_data --port 8000"
  fi
fi

if [ "$SKIP_TESTS" != true ]; then
  echo "[*] Running test suite..."
  python -m pytest tests/ || echo "[!] Some tests failed. This is normal if .env keys are not configured."
fi

echo "[*] Environment ready!"
echo "[*] Next steps:"
echo "    1. source .venv/bin/activate"
echo "    2. export PYTHONPATH=src"
echo "    3. Configure .env with your API keys"
echo "    4. Start ChromaDB: chroma run --path ./chroma_data --port 8000"
echo "    5. Index your knowledge base: python scripts/chroma_index.py"
echo "    6. Run FundRunner: PYTHONPATH=src python -m fundrunner.main"
