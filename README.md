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

`services/trading_daemon.py` provides a scheduler for automated trading with
limit checks.  Configure the behavior via environment variables defined in
`config.py`:

- `MAX_TRADES_PER_HOUR` – maximum trades allowed each hour
- `DAILY_STOP_LOSS` – cumulative loss threshold before trading stops
- `DAILY_PROFIT_TARGET` – profit target that disables trading for the day
- `PRE_MARKET_START` – UTC time when trading begins (e.g. `08:00`)
- `EXTENDED_HOURS_END` – UTC time when trading ends (e.g. `20:00`)

Trade statistics persist in `trading_state.json` and reset at the start of
each trading day.
