"""Gamma scalping utilities using Alpaca positions and orders.

This module implements :class:`GammaScalper`, a tiny helper that monitors the
net delta of option positions and hedges with the underlying stock when delta
moves away from a desired target.  It follows the high level approach outlined
in Alpaca's gamma scalping example algorithm.
"""

from __future__ import annotations

from typing import List, Dict

from alpaca.portfolio_manager import PortfolioManager
from alpaca.trade_manager import TradeManager


class GammaScalper:
    """Simple gamma scalping helper."""

    def __init__(self, portfolio: PortfolioManager, trader: TradeManager) -> None:
        """Create a new ``GammaScalper``.

        Parameters
        ----------
        portfolio:
            ``PortfolioManager`` used to fetch current positions.
        trader:
            ``TradeManager`` used to submit hedge orders.
        """

        self.portfolio = portfolio
        self.trader = trader

    def net_delta(self, symbol: str) -> float:
        """Compute the net delta exposure for ``symbol`` positions."""

        positions = self.portfolio.view_positions()
        return sum(
            p.get("delta", 0) * p.get("qty", 0)
            for p in positions
            if p.get("symbol") == symbol
        )

    def run(
        self, symbol: str, target_delta: float = 0.0, threshold: float = 0.1
    ) -> List[Dict[str, float]]:
        """Rebalance the delta for ``symbol`` if needed.

        Parameters
        ----------
        symbol:
            Underlying ticker symbol to hedge.
        target_delta:
            Desired aggregate delta of the position.
        threshold:
            Amount of delta drift tolerated before hedging.

        Returns
        -------
        list[dict[str, float]]
            A list of executed orders represented as dictionaries.
        """

        current_delta = self.net_delta(symbol)
        diff = current_delta - target_delta
        orders: List[Dict[str, float]] = []
        if abs(diff) > threshold:
            qty = int(abs(diff)) or 1
            if diff > 0:
                self.trader.sell(symbol, qty)
                orders.append({"symbol": symbol, "action": "sell", "qty": qty})
            else:
                self.trader.buy(symbol, qty)
                orders.append({"symbol": symbol, "action": "buy", "qty": qty})
        return orders
