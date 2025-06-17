# Trading Daemon API

The trading daemon exposes a very small HTTP interface for automating
order submission while the main CLI or other tools are running.

## Endpoints

- **GET `/status`** – Returns health information and mode flags
  (`MICRO_MODE`, `SIMULATION_MODE`).
- **POST `/orders`** – Submit a trade order. Body fields match those
  required by `TradeManager.buy`/`sell`.

```json
{
  "symbol": "AAPL",
  "qty": 1,
  "side": "buy",
  "order_type": "market",
  "time_in_force": "gtc"
}
```

The daemon is launched from the CLI and runs on port `8000`.
