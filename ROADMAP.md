# Yield Farming Development Roadmap

## Phase 1 – Stabilize Current Functionality

### Audit Lending Rate Handling
- Centralize rate fetching logic in services (e.g. `services/lending_rates.py`).
- Improve fallback stub data (include realistic spreads, variability).
- Add Alpaca API schema validation + error handling.

### Config & CLI Enhancements
- Expose more strategy parameters via `.env` and CLI (e.g. rebalance frequency, min allocation).
- Validate inputs (e.g. reject allocations > 100%).

### Logging & Notifications
- Extend `notifications.py` to log yield farming results (daily yields, failed API calls).
- Send portfolio rebalance alerts.

## Phase 2 – Data & Strategy Improvements

### Real Lending Rate Integrations
- Check Alpaca’s evolving stock-lending API.
- Add fallback sources (e.g. IBKR securities lending, Yahoo dividend yields).

### Yield Estimation Engine
- Combine lending + dividend yield.
- Support projected annualized return calculations.

### Backtesting Module
- Extend `backtester.py` to simulate yield farming over historical dividend + rate data.
- Plot PnL curves with `matplotlib` (hook into `dashboards/`).

## Phase 3 – Portfolio Management

### Position Sizing & Risk Controls
- Auto-adjust allocations when API returns fewer than `top_n`.
- Add diversification guardrails (e.g. sector cap, max % per ticker).

### Execution Layer
- Reuse `trading_daemon.py` but with a "lending strategy mode."
- Add dry-run mode for paper-trading.

### Rebalancing
- Background service (in `background_trader.py`) that checks rates periodically, triggers rebalance.

## Phase 4 – Monitoring & UX

### CLI Dashboard
- Show current portfolio yield, allocation breakdown, next rebalance time.

### Web Dashboard (optional)
- Build small FastAPI + Plotly/Dash module inside `dashboards/`.

### Performance Tracking
- Store portfolio history in SQLite (under `services/`).
- Generate reports on realized vs projected yields.

## Phase 5 – Deployment & Ops

### Robust Testing
- Unit tests for rate-fetching, portfolio allocation, rebalancing.
- Mock Alpaca API for CI.

### Background Mode
- Tie Yield Farming into `BACKGROUND_MODE.md` workflows.

### Docs
- Expand `README.md` with Yield Farming tutorial.
- Add diagrams of data flow (`docs/yield_farming_flow.md`).
