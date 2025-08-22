"""Automated background trading mode with periodic execution.

This service runs :class:`TradingBot` in an infinite loop, evaluating and
executing trades every ten minutes. Trades are confirmed automatically and up
to ninety percent of buying power is allocated, leaving a buffer for
rebalancing. A summary of the day's trades is printed at midnight.
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Dict, List

from rich.console import Console
from rich.table import Table

from fundrunner.alpaca.trading_bot import TradingBot
from fundrunner.utils.config import MICRO_MODE


async def run_background_mode(
    interval_minutes: int = 10,
    buffer: float = 0.1,
) -> None:
    """Run the trading bot periodically with automatic confirmation.

    Args:
        interval_minutes: Minutes between trading cycles.
        buffer: Fraction of buying power to retain for rebalancing.
    """
    console = Console()
    current_day = date.today()
    daily_trades: List[Dict] = []

    while True:
        bot = TradingBot(
            auto_confirm=True,
            vet_trade_logic=False,
            allocation_limit=1 - buffer,
            micro_mode=MICRO_MODE,
        )
        await bot.run()
        daily_trades.extend(bot.session_summary)

        now = datetime.now()
        if now.date() != current_day:
            _print_daily_summary(console, current_day, daily_trades)
            daily_trades.clear()
            current_day = now.date()
        await asyncio.sleep(interval_minutes * 60)


def _print_daily_summary(console: Console, day: date, trades: List[Dict]) -> None:
    """Display a summary of trades executed during the given day."""
    table = Table(title=f"Trade Summary {day.isoformat()}")
    table.add_column("Ticker", style="green")
    table.add_column("Action", style="cyan")
    table.add_column("Details", style="magenta")
    for trade in trades:
        table.add_row(
            str(trade.get("ticker", "")),
            str(trade.get("action", "")),
            str(trade.get("details", "")),
        )
    console.print(table)


def main() -> None:
    """Entry point for the background trading service."""
    asyncio.run(run_background_mode())


if __name__ == "__main__":
    main()
