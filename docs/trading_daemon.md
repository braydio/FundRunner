# Trading Daemon API

This daemon provides a lightweight HTTP interface for controlling the
`TradingBot`. It runs a Flask server on the URL defined by
`TRADING_DAEMON_URL` in `config.py` (defaults to `http://127.0.0.1:8000`).
The deprecated ``daemon_cli.py`` script has been removed—use ``curl`` or
another HTTP client to interact with the daemon.

## Endpoints

| Method | Path   | Description                                  |
| ------ | ------ | -------------------------------------------- |
| GET    | `/status` | Return JSON with daemon state (mode, paused, trade_count, daily_pl) |
| POST   | `/start` | Start/resume the trading loop (alias for `/resume`) |
| POST   | `/stop`  | Stop/pause the trading loop (alias for `/pause`) |
| POST   | `/pause` | Pause the trading loop |
| POST   | `/resume` | Resume the trading loop |
| POST   | `/mode`  | Set trading mode. Body: `{"mode": "stock"}` or `{"mode": "options"}` |
| POST   | `/order` | Submit an order. Body fields: `symbol`, `qty`, `side`, `order_type`, `time_in_force` |

## Configuration

The daemon respects the standard settings in `config.py`. Of note:

- `MICRO_MODE` — initial trading mode when the daemon starts.
- `PORTFOLIO_MANAGER_MODE` — enables passive portfolio management.
- `DEFAULT_TICKERS` and `EXCLUDE_TICKERS` — symbols evaluated by the bot.

These values can be overridden via environment variables before starting
the daemon.

## Examples

Start the server:

```bash
python trading_daemon.py
```

Switch to stock trading mode:

```bash
curl -X POST $TRADING_DAEMON_URL/mode -H 'Content-Type: application/json' \
     -d '{"mode": "stock"}'
```

Switch to options trading mode:

```bash
curl -X POST $TRADING_DAEMON_URL/mode -H 'Content-Type: application/json' \
     -d '{"mode": "options"}'
```

Submit a market order:

```bash
curl -X POST $TRADING_DAEMON_URL/order -H 'Content-Type: application/json' \
     -d '{"symbol": "AAPL", "qty": 1, "side": "buy"}'
```

Check status:

```bash
curl $TRADING_DAEMON_URL/status
```

