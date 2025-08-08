import pytest

from fundrunner.alpaca.portfolio_manager import PortfolioManager


class DummyClient:
    def __init__(self):
        self.orders = []

    def get_account(self):
        return {"portfolio_value": 1000}

    def list_positions(self):
        return []

    def get_latest_price(self, symbol):
        return 100.0

    def safe_float(self, val, default=0.0):
        try:
            return float(val)
        except Exception:
            return default

    def submit_order(self, symbol, qty, side, order_type, time_in_force):
        self.orders.append((symbol, qty, side, order_type, time_in_force))


class DummyRiskManager:
    def allocation_limit(self, symbol):
        return 0.1


def test_rebalance_applies_allocation_limit():
    client = DummyClient()
    pm = PortfolioManager(client=client, risk_manager=DummyRiskManager())
    pm.rebalance_portfolio({"AAPL": 0.5})
    assert client.orders == [("AAPL", pytest.approx(1.0), "buy", "market", "day")]
