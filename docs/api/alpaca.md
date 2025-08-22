## API Client (`api_client.py`)

The `AlpacaClient` class wraps the official [`alpaca-trade-api`](https://github.com/alpacahq/alpaca-trade-api-python) and provides structured methods for interacting with Alpaca.

### Authentication

- Uses `APCA_API_KEY_ID` and `APCA_API_SECRET_KEY` from environment.
- `BASE_URL` and `DATA_FEED` configured via `fundrunner.utils.config`.

### Methods Implemented

- **Account**

  - `get_account()` → `GET /v2/account`  
    Returns sanitized account info: cash, buying power, equity, portfolio value.

- **Orders**

  - `submit_order(symbol, qty, side, order_type, time_in_force)` → `POST /v2/orders`
  - `cancel_order(order_id)` → `DELETE /v2/orders/{id}`
  - `list_orders(status="open")` → `GET /v2/orders?status=open`

- **Positions**

  - `list_positions()` → `GET /v2/positions`  
    Returns list of positions with symbol, qty, value, entry price, current price, unrealized P/L.
  - `get_position(symbol)` → `GET /v2/positions/{symbol}`

- **Watchlists**

  - `list_watchlists()` → `GET /v2/watchlists`
  - `create_watchlist(name, symbols)` → `POST /v2/watchlists`
  - `add_to_watchlist(watchlist_id, symbol)` → `POST /v2/watchlists/{id}`
  - `remove_from_watchlist(watchlist_id, symbol)` → `DELETE /v2/watchlists/{id}/{symbol}`
  - `get_watchlist(watchlist_id)` → `GET /v2/watchlists/{id}`
  - `delete_watchlist(watchlist_id)` → `DELETE /v2/watchlists/{id}`

- **Market Data**
  - `get_historical_bars(symbol, days=30, timeframe=Day)` → `GET /v2/stocks/{symbol}/bars`
  - `get_latest_price(symbol)` → `GET /v2/stocks/{symbol}/trades/latest`

### Notes

- All responses are sanitized before return, ensuring floats are safely converted.
- Errors are logged and exceptions raised when API calls fail.
- Uses Alpaca’s **Data v2 API** for bars and trades.

---

## Next Steps

- [ ] Open `trading_bot.py` to see how `AlpacaClient` is orchestrated for real strategies.
- [ ] Document order lifecycle (submitted → open → filled → closed).
