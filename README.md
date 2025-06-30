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
├── main.py
├── backtester.py
├── transaction_logger.py
├── watchlist_view.py
├── config.py
```

## Setup

Install core dependencies for most functionality:

```bash
bash scripts/setup.sh
```

To include optional plugin packages, pass `--plugins`:

```bash
bash scripts/setup.sh --plugins
```

You can also install the plugin requirements manually:

```bash
pip install -r requirements-plugins.txt
```

## Micro Mode

Set `MICRO_MODE=true` in your `.env` file to run the bot assuming a small
simulated account balance.  `MICRO_ACCOUNT_SIZE` controls the starting cash
when micro mode is enabled (defaults to `$100`).  This mode automatically
increases trade allocation limits so the bot can purchase at least one share
when funds allow.

## Market Data Feed

Set `ALPACA_DATA_FEED` in your `.env` to control which Alpaca market data feed
is used. Free accounts should use `iex`; paid subscriptions may specify `sip`.

## Trading Daemon

A lightweight asynchronous service located in `services/trading_daemon.py` exposes Flask endpoints for controlling trading bots at runtime. Start it with `python services/trading_daemon.py` and interact via `/status`, `/pause`, `/resume`, `/mode`, and `/order` endpoints.

## Plugin Tools Menu

For quick experimentation with optional plugins, run the interactive console:

```bash
python plugin_tools_menu.py
```

This menu demonstrates plotting, portfolio optimization and sentiment analysis without launching the full bot.
