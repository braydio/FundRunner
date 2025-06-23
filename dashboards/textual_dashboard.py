"""Textual dashboard application for interactive trading data display.

This module defines :class:`DashboardApp`, an asynchronous application built with
textual. It shows three tables for trade evaluations, the trade tracker, and the
portfolio. Data is pushed into async queues that the app consumes to update the
widgets.
"""

from __future__ import annotations

import asyncio
from typing import Iterable

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import DataTable, Static


class DashboardApp(App):
    """Textual application displaying trading tables."""

    CSS = """
    Screen {
        layout: horizontal;
    }
    """

    def __init__(
        self,
        eval_queue: asyncio.Queue[Iterable[str]],
        trade_queue: asyncio.Queue[Iterable[str]],
        portfolio_queue: asyncio.Queue[Iterable[str]],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.eval_queue = eval_queue
        self.trade_queue = trade_queue
        self.portfolio_queue = portfolio_queue
        self.eval_table = DataTable(zebra_stripes=True)
        self.trade_table = DataTable(zebra_stripes=True)
        self.portfolio_table = DataTable(zebra_stripes=True)

    def compose(self) -> ComposeResult:
        self.eval_table.add_columns(
            "Ticker",
            "Current Price",
            "Probability",
            "Expected Net",
            "Decision",
        )
        self.trade_table.add_columns(
            "Symbol",
            "Entry",
            "Stop",
            "Target",
            "ES",
            "Status",
        )
        self.portfolio_table.add_columns(
            "Symbol",
            "Qty",
            "Avg Entry",
            "Current Price",
            "P/L$",
        )
        yield Horizontal(
            self.eval_table,
            self.trade_table,
            self.portfolio_table,
        )

    async def on_mount(self) -> None:
        self.set_interval(0.1, self._poll_queues)

    async def _poll_queues(self) -> None:
        while not self.eval_queue.empty():
            row = await self.eval_queue.get()
            self.eval_table.add_row(*[str(x) for x in row])
        while not self.trade_queue.empty():
            row = await self.trade_queue.get()
            self.trade_table.add_row(*[str(x) for x in row])
        while not self.portfolio_queue.empty():
            row = await self.portfolio_queue.get()
            self.portfolio_table.add_row(*[str(x) for x in row])

