# Textual Dashboard

The `DashboardApp` in `dashboards/textual_dashboard.py` provides a simple
[TUI](https://github.com/Textualize/textual) interface showing three tables:
trade evaluations, the trade tracker and the current portfolio. The app runs as
an asynchronous task and receives row data via three `asyncio.Queue` objects.

## Setup

Install dependencies including `textual`:

```bash
pip install -r requirements.txt
```

## Example Usage

```python
from alpaca.trading_bot import TradingBot

bot = TradingBot(auto_confirm=True, vet_trade_logic=False)
asyncio.run(bot.run())
```

The bot launches the dashboard automatically. Press `q` to quit the dashboard.
