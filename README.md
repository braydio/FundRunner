```
project/
├── src/
│   └── fundrunner/
│       ├── alpaca/
│       ├── bots/
│       ├── options/
│       ├── services/
│       ├── dashboards/
│       ├── plugins/
│       └── utils/
└── tests/
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

## Portfolio Manager Mode

Set `PORTFOLIO_MANAGER_MODE=true` to run the bot in a passive mode that focuses
on monitoring account risk and rebalancing the overall portfolio. In this mode
the bot only adjusts positions periodically based on portfolio analysis instead
of evaluating individual trades.

## Market Data Feed

Set `ALPACA_DATA_FEED` in your `.env` to control which Alpaca market data feed
is used. Free accounts should use `iex`; paid subscriptions may specify `sip`.

## Trading Daemon

A lightweight asynchronous service located in `services/trading_daemon.py` exposes Flask endpoints for controlling trading bots at runtime. Start it with `python services/trading_daemon.py` and interact via `/status`, `/pause`, `/resume`, `/mode`, and `/order` endpoints. Use `curl` or another HTTP client to issue commands; the old `daemon_cli.py` helper has been removed.

## Plugin Tools Menu

For quick experimentation with optional plugins, run the interactive console:

```bash
python plugin_tools_menu.py
```

This menu demonstrates plotting, portfolio optimization and sentiment analysis without launching the full bot.

## Notifications

FundRunner can alert on trades or risk events via email and Discord. Configure
the following environment variables in your `.env` file:

- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`,
  `NOTIFICATION_EMAIL` – SMTP settings for outbound email.
- `DISCORD_WEBHOOK_URL` – Discord webhook URL for channel alerts.

## Maintenance Mode

After each trading session, the bot automatically enters a short
maintenance phase. During this mode it repeatedly reviews open
positions, compares them against the original trade forecast and
updates the textual dashboard with any notable changes. By default it
runs for five cycles with a 60 second pause between checks.

## Configuration Menu

Run `python main.py` and choose option `14` to view the current environment
configuration.  Secret keys are shown only as `SET` or `NOT SET` so you can
verify that `.env` values loaded correctly.
