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

The Alpaca trading API base URL is configured via `ALPACA_BASE_URL` and the
market data API via `ALPACA_DATA_URL` in your `.env` file. Both default to the
paper trading and data endpoints.

## Dependencies

The project ships with a small HTTP daemon for controlling the bot. See
[docs/trading_daemon.md](docs/trading_daemon.md) for endpoint details and usage
examples.
