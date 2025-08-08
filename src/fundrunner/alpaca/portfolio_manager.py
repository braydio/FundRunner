
"""Portfolio utilities backed by the Alpaca API.

In addition to view helpers, this module provides rebalancing that respects
allocation limits from :class:`~fundrunner.alpaca.risk_manager.RiskManager`.
"""

from fundrunner.alpaca.api_client import AlpacaClient
from fundrunner.alpaca.risk_manager import RiskManager

class PortfolioManager:
    def __init__(
        self,
        client: AlpacaClient | None = None,
        risk_manager: RiskManager | None = None,
    ) -> None:
        """Initialize portfolio and risk managers."""

        self.client = client or AlpacaClient()
        self.risk_manager = risk_manager or RiskManager(client=self.client)

    def view_account(self):
        return self.client.get_account()

    def view_positions(self):
        return self.client.list_positions()

    def view_position(self, symbol):
        return self.client.get_position(symbol)

    def rebalance_portfolio(self, target_allocations: dict[str, float]) -> None:
        """Rebalance holdings to ``target_allocations`` applying risk limits.

        Parameters
        ----------
        target_allocations:
            Mapping of ticker symbols to desired portfolio weights expressed as
            fractions of total portfolio value.
        """

        account = self.client.get_account()
        portfolio_value = self.client.safe_float(account.get("portfolio_value"))
        positions = {
            p["symbol"]: self.client.safe_float(p.get("qty"))
            for p in self.client.list_positions()
        }

        for symbol, weight in target_allocations.items():
            price = self.client.get_latest_price(symbol)
            if price is None or portfolio_value == 0:
                continue

            limit = self.risk_manager.allocation_limit(symbol)
            max_value = portfolio_value * limit
            desired_value = min(portfolio_value * weight, max_value)
            target_qty = desired_value / price

            current_qty = positions.get(symbol, 0)
            diff = target_qty - current_qty
            if diff > 0:
                self.client.submit_order(symbol, diff, "buy", "market", "day")
            elif diff < 0:
                self.client.submit_order(symbol, abs(diff), "sell", "market", "day")

