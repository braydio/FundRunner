"""Rich dashboard utilities for displaying bot tables.

This module defines :class:`Dashboard`, a wrapper around ``rich.Live`` that
maintains persistent tables for trade evaluations, tracked trades, and the
portfolio. Tables are updated in-place and re-rendered through ``Live`` only
when data changes.
"""

from __future__ import annotations

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table


class Dashboard:
    """Manage persistent trading tables and live rendering."""

    def __init__(self, console: Console, refresh_per_second: int = 2) -> None:
        self.console = console
        self.summary_table = self._create_summary_table()
        self.trade_tracker_table = self._create_trade_tracker_table()
        self.portfolio_table = self._create_portfolio_table()
        self._live = Live(
            self._group(), console=console, refresh_per_second=refresh_per_second
        )

    @property
    def live(self) -> Live:
        """Return the underlying :class:`Live` instance."""
        return self._live

    def _group(self) -> Group:
        return Group(
            Panel(self.summary_table, title="Trade Evaluations"),
            Panel(self.trade_tracker_table, title="Trade Tracker"),
            Panel(self.portfolio_table, title="Portfolio Positions"),
        )

    def start(self) -> None:
        """Start live rendering."""
        self._live.start()

    def stop(self) -> None:
        """Stop live rendering."""
        self._live.stop()

    def refresh(self) -> None:
        """Redraw the dashboard with current table contents."""
        self._live.update(self._group())

    @staticmethod
    def _create_summary_table() -> Table:
        table = Table(title="Trade Evaluation Summary")
        table.add_column("Ticker", style="bold green")
        table.add_column("Current Price", justify="right", style="cyan")
        table.add_column("Probability", justify="right", style="magenta")
        table.add_column("Expected Net", justify="right", style="yellow")
        table.add_column("Decision", style="bold red")
        return table

    @staticmethod
    def _create_trade_tracker_table() -> Table:
        table = Table(title="Trade Tracker")
        table.add_column("Symbol", justify="center", style="green")
        table.add_column("Entry Price", justify="right", style="cyan")
        table.add_column("Stop Loss", justify="right", style="red")
        table.add_column("Profit Target", justify="right", style="magenta")
        table.add_column("ES Metric", justify="right", style="yellow")
        table.add_column("Status", justify="center", style="bold")
        return table

    @staticmethod
    def _create_portfolio_table() -> Table:
        table = Table(title="Live Portfolio Positions", style="bold blue")
        table.add_column("Symbol", justify="center", style="green")
        table.add_column("Qty", justify="right", style="cyan")
        table.add_column("Avg Entry", justify="right", style="magenta")
        table.add_column("Current Price", justify="right", style="yellow")
        table.add_column("$ P/L", justify="right", style="red")
        return table
