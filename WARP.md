# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## What is FundRunner

FundRunner is a comprehensive algorithmic trading application that integrates with Alpaca Markets for equity and options trading. It features interactive CLI interfaces, automated trading bots, portfolio management tools, and a Flask-based daemon for continuous operation.

⚠️ **SAFETY NOTE**: Always use paper trading endpoints for development and testing. Verify your `ALPACA_BASE_URL` points to `https://paper-api.alpaca.markets` before running any trading operations.

## Quickstart (5-10 minutes)

### Prerequisites
- Python 3.10+ 
- Git
- curl (for daemon API calls)
- macOS/Linux (WSL supported)

### Setup Environment
```bash
# Clone and setup virtual environment
bash scripts/setup.sh
source .venv/bin/activate

# For optional plugins (ML, visualization, portfolio optimization)
bash scripts/setup.sh --plugins

# Configure environment
cp .env.example .env
# Edit .env with your API keys - recommend starting with:
# SIMULATION_MODE=true
# ALPACA_BASE_URL=https://paper-api.alpaca.markets
```

### Essential Environment Setup
```bash
# Set Python path for src-layout imports
export PYTHONPATH=src

# Verify setup
PYTHONPATH=src python -m fundrunner.main
```

This launches the interactive CLI where you can view account info (option 1) and run the trading bot (option 8).

## Common Commands Cheat Sheet

### Setup and Environment
```bash
# Initial setup
bash scripts/setup.sh
source .venv/bin/activate
export PYTHONPATH=src

# Install plugins 
bash scripts/setup.sh --plugins
# Or manually: pip install -r requirements-plugins.txt

# Lint code
./scripts/lint.sh

# Run tests (requires valid .env or mocks)
python -m unittest discover tests/
```

### Application Execution
```bash
# Interactive CLI
PYTHONPATH=src python -m fundrunner.main

# Trading Daemon (Flask server + async trading loop)
PYTHONPATH=src python -m fundrunner.services.trading_daemon

# Plugin Tools Menu
python plugin_tools_menu.py
```

### Daemon HTTP Control
```bash
# Status and control
curl $TRADING_DAEMON_URL/status
curl -X POST $TRADING_DAEMON_URL/pause
curl -X POST $TRADING_DAEMON_URL/resume

# Switch trading mode
curl -X POST $TRADING_DAEMON_URL/mode \
  -H 'Content-Type: application/json' \
  -d '{"mode":"stock"}'    # or "options"

# Submit order
curl -X POST $TRADING_DAEMON_URL/order \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"AAPL","qty":1,"side":"buy"}'
```

## Architecture Overview

### Module Structure
```
src/fundrunner/
├── alpaca/         # API client, managers, trading bot core
├── bots/           # Strategy bots (options, ChatGPT controller)  
├── dashboards/     # Rich/Textual UI components
├── options/        # Options trading utilities
├── plugins/        # Optional ML/analysis tools
├── services/       # Trading daemon (Flask + async)
├── utils/          # Config, logging, transaction tracking
fundrunner/         # Legacy entry points (being migrated)
scripts/            # Setup and linting utilities
tests/              # Unit tests with monkeypatch examples
```

### Data Flow
```
CLI Interface (main.py)
    ↓
TradeManager/PortfolioManager/WatchlistManager  
    ↓
AlpacaClient (api_client.py)
    ↓
Alpaca Markets API

Trading Daemon (services/trading_daemon.py)
    ↓
Flask Endpoints ← → Async Trading Loop
    ↓
TradingBot or run_options_analysis
    ↓ 
Transaction Logger + Dashboard Updates
```

### Key Components
- **TradingBot**: Main trading logic with LLM vetting, risk management, and dashboard integration
- **Trading Daemon**: Flask API + asyncio loop for continuous operation
- **Portfolio Managers**: Account monitoring, position tracking, P/L calculation
- **Plugin System**: Optional tools for sentiment analysis, portfolio optimization, plotting

## Configuration and Environment Variables

### Alpaca API
```bash
ALPACA_API_KEY=your_key_here
ALPACA_API_SECRET=your_secret_here  
ALPACA_BASE_URL=https://paper-api.alpaca.markets  # Paper trading
ALPACA_DATA_URL=https://data.alpaca.markets
ALPACA_DATA_FEED=iex  # or sip for paid subscriptions
```

### AI Integration
```bash
OPENAI_API_KEY=your_openai_key
GPT_MODEL=gpt-4o-mini
USE_LOCAL_LLM=false
LOCAL_LLM_API_URL=http://localhost:5051/v1/chat
LOCAL_LLM_API_KEY=your_local_key
```

### Trading Configuration
```bash
DEFAULT_TICKERS=AAPL,MSFT,GOOGL,AMZN,FB
EXCLUDE_TICKERS=
DEFAULT_TICKERS_FROM_GPT=false
```

### Operating Modes
```bash
SIMULATION_MODE=true
SIMULATED_STARTING_CASH=5000
MICRO_MODE=false         # Small account mode
MICRO_ACCOUNT_SIZE=100   # Overrides SIMULATED_STARTING_CASH when enabled
PORTFOLIO_MANAGER_MODE=false  # Passive rebalancing vs active trading
```

### Trading Daemon
```bash
TRADING_DAEMON_URL=http://127.0.0.1:8000
MAX_TRADES_PER_HOUR=10
DAILY_STOP_LOSS=1000
DAILY_PROFIT_TARGET=1000
PRE_MARKET_START=08:00
EXTENDED_HOURS_END=20:00
```

### Optional Services
```bash
# Tradier for options data
TRADIER_API_KEY=your_tradier_key

# Email notifications
SMTP_SERVER=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_password
NOTIFICATION_EMAIL=recipient@example.com
```

## Operating Modes

### Simulation Mode
- Runs without placing live orders
- Tracks P/L against `SIMULATED_STARTING_CASH`
- Safe for development and testing
- Enable with: `SIMULATION_MODE=true`

### Micro Mode  
- Designed for small account balances
- Increases allocation limits to ensure trades can execute
- Uses `MICRO_ACCOUNT_SIZE` as starting cash
- Enable with: `MICRO_MODE=true`

### Portfolio Manager Mode
- Focuses on portfolio rebalancing vs individual trade evaluation
- Passive monitoring and periodic adjustments
- Enable with: `PORTFOLIO_MANAGER_MODE=true`

### Maintenance Mode
- Automatically triggered after trading sessions
- Reviews open positions against original forecasts
- Updates textual dashboard with changes
- Runs 5 cycles with 60-second intervals

## Trading Daemon Usage

The trading daemon provides a Flask HTTP interface for controlling the trading bot programmatically.

### Available Endpoints
- `GET /status` - Current daemon status and mode
- `POST /pause` - Pause trading loop
- `POST /resume` - Resume trading loop  
- `POST /mode` - Switch between "stock" and "options" modes
- `POST /order` - Submit manual order

### Example Usage
```bash
# Start daemon
PYTHONPATH=src python -m fundrunner.services.trading_daemon

# Check status
curl http://127.0.0.1:8000/status

# Switch to options trading
curl -X POST http://127.0.0.1:8000/mode \
  -H 'Content-Type: application/json' \
  -d '{"mode":"options"}'
```

## Optional Plugins and Tools

### Installation
```bash
# Install all plugins
bash scripts/setup.sh --plugins

# Available plugins: transformers, torch, tiktoken, openai, PyPortfolioOpt, mplfinance
```

### Plugin Tools Menu
```bash
python plugin_tools_menu.py
```

Provides interactive access to:
- Portfolio optimization
- Trade plotting and visualization  
- Sentiment analysis using FinBERT
- Multi-metric analysis

⚠️ **Note**: ML plugins may download large models and benefit from GPU acceleration.

## Development Workflow

### Environment Setup
```bash
source .venv/bin/activate
export PYTHONPATH=src
```

### Code Quality
```bash
# Lint with flake8
./scripts/lint.sh

# Run tests
python -m unittest discover tests/
```

### Testing Notes
- Some tests require valid API keys in `.env`
- Monkeypatch examples available in `tests/`
- Use `SIMULATION_MODE=true` for safe testing

### Contribution Guidelines
- Branch naming: `feature/*` or `fix/*`
- Reference `AGENTS.md` for detailed contributor guide
- Never commit `.env` or secrets
- Update API documentation in `docs/api/` when adding endpoints

## Troubleshooting and Known Issues

### Import Errors
**Issue**: `ModuleNotFoundError` when running applications
**Solution**: Ensure `PYTHONPATH=src` is set

### Port Conflicts  
**Issue**: Trading daemon fails to start on port 8000
**Solution**: Change `TRADING_DAEMON_URL` or modify Flask port in daemon code

### Test Failures
**Issue**: Tests fail with API connection errors
**Solution**: Set `SIMULATION_MODE=true` and provide dummy keys or use test mocks

### CLI Menu Issues
**Issue**: Duplicate option "14" in main menu
**Status**: Known issue in `fundrunner/main.py` - workaround available

### Daemon Endpoint Mismatch
**Issue**: CLI references `/start` and `/stop` endpoints that don't exist in current daemon
**Actual endpoints**: Use `/pause` and `/resume` instead
**Status**: Documentation and code alignment in progress

## Warp Workflows

### Daily Development Setup
```bash
# Initialize environment
source .venv/bin/activate
export PYTHONPATH=src

# Load environment variables
source .env

# Quick status check
PYTHONPATH=src python -c "from fundrunner.utils.config import *; print(f'Simulation: {SIMULATION_MODE}, Micro: {MICRO_MODE}')"
```

### Testing Workflow
```bash
# Lint and test
./scripts/lint.sh && python -m unittest discover tests/

# Run specific trading bot test
python -m unittest tests.test_trading_bot -v
```

### Daemon Control Workflow
```bash
# Start daemon in background
PYTHONPATH=src nohup python -m fundrunner.services.trading_daemon &

# Control daemon
curl -X POST $TRADING_DAEMON_URL/pause
curl $TRADING_DAEMON_URL/status
curl -X POST $TRADING_DAEMON_URL/resume
```

## Build and Test Commands

### Core Commands
```bash
# Setup virtual environment and dependencies
bash scripts/setup.sh

# Setup with optional ML/analysis plugins
bash scripts/setup.sh --plugins

# Activate environment
source .venv/bin/activate

# Set Python path for imports
export PYTHONPATH=src

# Run linting
./scripts/lint.sh

# Execute test suite
python -m unittest discover tests/

# Run single test file
python -m unittest tests.test_api_client_positions -v
```

### Application Execution
```bash
# Interactive CLI menu
PYTHONPATH=src python -m fundrunner.main

# Start trading daemon
PYTHONPATH=src python -m fundrunner.services.trading_daemon

# Run one-time trading bot
PYTHONPATH=src python -c "
import asyncio
from fundrunner.alpaca.trading_bot import TradingBot
bot = TradingBot(auto_confirm=False)
asyncio.run(bot.run())
"
```

## High-Level Architecture

FundRunner follows a modular architecture with clear separation between user interfaces, business logic, and external integrations:

**Interactive Layer**
- CLI Menu (`fundrunner.main`) - Interactive terminal interface
- Trading Daemon (`services.trading_daemon`) - HTTP API + async trading loop

**Business Logic Layer**  
- Trading Bots (`alpaca.trading_bot`, `bots.*`) - Core trading strategies
- Managers (`alpaca.*_manager`) - Portfolio, trade, and watchlist management
- Risk Management (`alpaca.risk_manager`) - Position sizing and safety controls

**Integration Layer**
- Alpaca Client (`alpaca.api_client`) - Market data and order routing
- LLM Integration (`alpaca.llm_vetter`, `bots.chatgpt_*`) - AI-powered analysis
- External Data (`options.live_options_api`) - Options chain data

**Support Services**
- Configuration (`utils.config`) - Environment variable management
- Logging (`utils.transaction_logger`) - Trade history and audit trail
- Dashboards (`dashboards.*`) - Real-time monitoring interfaces

This architecture enables flexible deployment patterns - from interactive development sessions to fully automated trading systems.

---

*Last updated: 2025-01-22*
*For questions or issues, refer to AGENTS.md or the docs/ directory*
