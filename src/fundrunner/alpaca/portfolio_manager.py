
"""Utilities for interacting with the Alpaca account and positions.

This module exposes a thin wrapper around :class:`AlpacaClient` and now also
provides an asynchronous ``run_active_management`` coroutine used by the trading
daemon to perform periodic portfolio maintenance.
"""

from __future__ import annotations

import asyncio

from fundrunner.alpaca.api_client import AlpacaClient


class PortfolioManager:
    """High-level helper for portfolio operations."""

    def __init__(self) -> None:
        self.client = AlpacaClient()

    def view_account(self):
        """Return account information from Alpaca."""
        return self.client.get_account()

    def view_positions(self):
        """Return all open positions."""
        return self.client.list_positions()

    def view_position(self, symbol):
        """Return a single position for ``symbol``."""
        return self.client.get_position(symbol)

    async def run_active_management(self) -> None:
        """Placeholder loop for active portfolio management.

        The real implementation would periodically rebalance or otherwise manage
        the portfolio. For now it simply sleeps to simulate work so the trading
        daemon can coordinate starting and stopping the task.
        """

        while True:
            await asyncio.sleep(60)

