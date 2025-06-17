# Trading Daemon API

This daemon provides a lightweight HTTP interface for controlling the
`TradingBot`. It runs a Flask server on the URL defined by
`TRADING_DAEMON_URL` in `config.py` (defaults to `http://127.0.0.1:8000`).

## Endpoints

| Method | Path   | Description                                  |
| ------ | ------ | -------------------------------------------- |
| POST   | `/start` | Start the trading bot if not already running |
| POST   | `/stop`  | Stop the running bot                         |
| GET    | `/status` | Return JSON with `running` and current `mode` |
| POST   | `/mode`  | Set trading mode. Body: `{"mode": "micro"}` or `{"mode": "standard"}` |
| POST   | `/order` | Submit an order while the daemon is active. Body fields: `symbol`, `qty`, `side`, `order_type`, `time_in_force` |

## Configuration

The daemon respects the standard settings in `config.py`. Of note:

- `MICRO_MODE` — initial trading mode when the daemon starts.
- `DEFAULT_TICKERS` and `EXCLUDE_TICKERS` — symbols evaluated by the bot.

These values can be overridden via environment variables before starting
the daemon.

## Examples

Start the server:

```bash
python trading_daemon.py
```

Switch to micro mode via HTTP:

```bash
curl -X POST $TRADING_DAEMON_URL/mode -H 'Content-Type: application/json' \
     -d '{"mode": "micro"}'
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

