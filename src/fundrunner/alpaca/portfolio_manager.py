"""Simplified wrappers for viewing and adjusting an Alpaca portfolio."""

from typing import Iterable

from fundrunner.alpaca.api_client import AlpacaClient
from fundrunner.alpaca.trade_manager import TradeManager
from fundrunner.services.notifications import notify


class PortfolioManager:
    def __init__(self) -> None:
        self.client = AlpacaClient()
        self.trader = TradeManager()

    def view_account(self):
        return self.client.get_account()

    def view_positions(self):
        return self.client.list_positions()

    def view_position(self, symbol):
        return self.client.get_position(symbol)

    def rebalance_portfolio(self, trades: Iterable[dict]) -> list:
        """Execute trades and send notifications.

        Args:
            trades (Iterable[dict]):
                Each trade dict requires ``symbol``, ``qty`` and ``side`` keys.

        Returns:
            list: Orders returned by the trade manager.
        """
        orders = []
        for trade in trades:
            side = trade.get("side", "buy").lower()
            symbol = trade["symbol"]
            qty = trade["qty"]
            order_type = trade.get("order_type", "market")
            tif = trade.get("time_in_force", "gtc")
            if side == "buy":
                order = self.trader.buy(symbol, qty, order_type, tif)
            else:
                order = self.trader.sell(symbol, qty, order_type, tif)
            notify("Rebalance Trade Executed", f"{side} {qty} {symbol}")
            orders.append(order)
        return orders
