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

## Services

### Trading Daemon

An asynchronous trading service is available in `services/trading_daemon.py`.
Start it with:

```bash
python -m services.trading_daemon
```

This daemon exposes Flask endpoints for runtime control:

- `/status` – retrieve the current mode and pause state
- `/order` – submit a market order (POST)
- `/pause` – pause trading activity (POST)
- `/resume` – resume trading activity (POST)
- `/mode` – switch between `stocks` and `options` modes (POST)
