```
project/
├── alpaca/
│   ├── __init__.py
│   ├── api_client.py
│   ├── portfolio_manager.py
│   ├── trade_manager.py
│   └── watchlist_manager.py
├── options/
│   ├── __init__.py
│   └── options_integration.py
├── llm_integration.py
├── logger_config.py
├── cli.py
├── main.py
├── backtester.py
├── transaction_logger.py
├── config.py
```

## Micro Mode

Set `MICRO_MODE=true` in your `.env` file to run the bot assuming a small
simulated account balance.  `MICRO_ACCOUNT_SIZE` controls the starting cash
when micro mode is enabled (defaults to `$100`).  This mode automatically
increases trade allocation limits so the bot can purchase at least one share
when funds allow.

## Trading Daemon

Run `python main.py` and choose **Start Trading Daemon** to launch a small HTTP
service exposing trading actions. The daemon listens on port `8000` by default
and provides these endpoints:

- `GET /status` – Check that the service is running and view current mode flags.
- `POST /orders` – Submit an order with JSON payload:

  ```json
  {
    "symbol": "AAPL",
    "qty": 1,
    "side": "buy",
    "order_type": "market",
    "time_in_force": "gtc"
  }
  ```

### Switching Modes

Set `MICRO_MODE` or `SIMULATION_MODE` in `.env` before starting the daemon to
control trading behaviour. `GET /status` reflects the current values.

With the daemon running you can send orders using `curl`:

```bash
curl -X POST http://localhost:8000/orders \
     -H 'Content-Type: application/json' \
     -d '{"symbol":"AAPL","qty":1,"side":"buy"}'
```
