# Alpaca Integration (FundRunner)

FundRunner integrates with the [Alpaca Markets API](https://alpaca.markets/docs/) for trading, portfolio management, watchlists, and market data.

All Alpaca-related code is under `src/fundrunner/alpaca/`.

---

## API Client (`api_client.py`)

The `AlpacaClient` class wraps the official [`alpaca-trade-api`](https://github.com/alpacahq/alpaca-trade-api-python) and provides structured methods for interacting with Alpaca.

### Authentication

- `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` from environment.
- `APCA_API_BASE_URL` and `DATA_FEED` configured via `fundrunner.utils.config`.

### Methods Implemented

**Account**

- `get_account()` → `GET /v2/account`  
  Returns account info: cash, buying power, equity, portfolio value.

**Orders**

- `submit_order(symbol, qty, side, order_type, time_in_force)` → `POST /v2/orders`
- `cancel_order(order_id)` → `DELETE /v2/orders/{id}`
- `list_orders(status="open")` → `GET /v2/orders?status=open`

**Positions**

- `list_positions()` → `GET /v2/positions`
- `get_position(symbol)` → `GET /v2/positions/{symbol}`

**Watchlists**

- `list_watchlists()` → `GET /v2/watchlists`
- `create_watchlist(name, symbols)` → `POST /v2/watchlists`
- `add_to_watchlist(watchlist_id, symbol)` → `POST /v2/watchlists/{id}`
- `remove_from_watchlist(watchlist_id, symbol)` → `DELETE /v2/watchlists/{id}/{symbol}`
- `get_watchlist(watchlist_id)` → `GET /v2/watchlists/{id}`
- `delete_watchlist(watchlist_id)` → `DELETE /v2/watchlists/{id}`

**Market Data**

- `get_historical_bars(symbol, days=30, timeframe=Day)` → `GET /v2/stocks/{symbol}/bars`
- `get_latest_price(symbol)` → `GET /v2/stocks/{symbol}/trades/latest`

### Notes

- Responses are sanitized (floats normalized).
- Exceptions raised on failed API calls.
- Uses Alpaca **Data v2 API**.

---

## Trading Bot (`trading_bot.py`)

The `TradingBot` orchestrates Alpaca trading sessions.

### Responsibilities

- Initialize `AlpacaClient` and verify account connection.
- Load/watch positions, orders, and watchlists.
- Execute strategies by combining:
  - Watchlist candidates
  - Risk manager constraints
  - Portfolio manager targets
- Submit/manage trades through `AlpacaClient`.

### Features

- **Modes**
  - _Micro Mode_: $100 default account balance for small-scale testing.
  - _Portfolio Manager Mode_: Rebalancing across positions.
- **Order Lifecycle**
  1. Candidate symbol generated
  2. Risk checks applied
  3. Order submitted
  4. Status monitored until filled/canceled
  5. Position updated
- **Error Handling**
  - Retries failed API calls
  - Logs all failures
- **Extensibility**
  - Risk manager, portfolio manager, yield farming hooks
  - Plugin advisors (`chatgpt_advisor`, `llm_vetter`)

---

## Risk Manager (`risk_manager.py`)

The `RiskManager` enforces dynamic position sizing and probability thresholds.

### Parameters

- `base_allocation_limit`: 5% of buying power default
- `base_risk_threshold`: 0.6 default (probability of profit)
- `minimum_allocation`: 1% minimum allocation floor

### Logic

- Fetches 30-day bar history from Alpaca.
- Computes volatility (std of daily returns).
- Adjusts allocation:
  - Downward when volatility is high
  - Reduced further for low-volume symbols
  - Floors at minimum allocation
- Adjusts risk threshold:
  - Higher confidence required in volatile markets
  - Cap < 0.9

### Output

Returns `(allocation_limit, risk_threshold)` to guide order submission.

---

## Portfolio Manager (`portfolio_manager.py`)

A lightweight wrapper for account & position viewing.

### Methods

- `view_account()` → wraps `AlpacaClient.get_account()`
- `view_positions()` → wraps `AlpacaClient.list_positions()`
- `view_position(symbol)` → wraps `AlpacaClient.get_position(symbol)`

### Purpose

- Provides simplified access for dashboards or strategies.
- Avoids exposing full `AlpacaClient` internals.

---

## Active Portfolio Manager (`portfolio_manager_active.py`)

Provides utilities for **active portfolio rebalancing**.

### Functions

- `calculate_weights(positions)` → compute position weights by market value.
- `parse_target_weights(spec)` → parse user strings like `"AAPL:0.6,MSFT:0.4"`.
- `rebalance_decisions(positions, target_weights, prices)` → calculate buy/sell qty adjustments.

---

## Trade Manager (`trade_manager.py`)

Convenience wrapper for trade execution.

### Methods

- `buy(symbol, qty, order_type='market', time_in_force='gtc')`
- `sell(symbol, qty, order_type='market', time_in_force='gtc')`
- `cancel_order(order_id)`
- `list_open_orders()`

---

## Watchlist Manager (`watchlist_manager.py`)

Helpers for managing watchlists.

### Methods

- `list_watchlists()`
- `create_watchlist(name, symbols)`
- `add_to_watchlist(watchlist_id, symbol)`
- `remove_from_watchlist(watchlist_id, symbol)`
- `get_watchlist(watchlist_id)`
- `delete_watchlist(watchlist_id)`

---

## Yield Farmer (`yield_farming.py`)

Implements yield-focused strategies.

### Stock Lending

- `build_lending_portfolio(allocation_percent=0.5, top_n=3)` → construct portfolio of top lending-rate stocks using `LendingRateService`.

### Dividend Capture

- `fetch_dividend_info(symbol)` → get dividend yield & ex-date via Yahoo Finance.
- `build_dividend_portfolio(symbols, allocation_percent=0.5, active=False)` → build portfolio based on dividend yields.

---

# Next Steps

- Integrate yield farming into `TradingBot`.
- Add advisor modules (`chatgpt_advisor.py`, `llm_vetter.py`) under plugin integrations.
- Provide strategy templates (momentum, value, income).
