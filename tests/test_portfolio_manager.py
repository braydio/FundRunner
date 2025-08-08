import json
from pathlib import Path

import pytest

from fundrunner.alpaca import portfolio_manager as pm_mod


class DummyClient:
    def __init__(self, positions):
        self._positions = positions
        self.orders = []

    def list_positions(self):
        return self._positions

    def get_account(self):
        return {}

    def get_position(self, symbol):
        for p in self._positions:
            if p["symbol"] == symbol:
                return p
        return None

    def submit_order(self, symbol, qty, side, order_type, time_in_force):
        self.orders.append((symbol, qty, side))
        return {
            "symbol": symbol,
            "qty": qty,
            "side": side,
        }


def make_manager(monkeypatch, positions):
    mgr = pm_mod.PortfolioManager()
    mgr.client = DummyClient(positions)
    return mgr


def test_calculate_current_weights(monkeypatch):
    positions = [
        {"symbol": "AAPL", "market_value": 100},
        {"symbol": "MSFT", "market_value": 300},
    ]
    mgr = make_manager(monkeypatch, positions)
    weights = mgr.calculate_current_weights()
    assert pytest.approx(weights["AAPL"]) == 0.25
    assert pytest.approx(weights["MSFT"]) == 0.75


def test_determine_target_weights_persistence(monkeypatch, tmp_path):
    positions = [
        {"symbol": "AAPL", "market_value": 100},
        {"symbol": "MSFT", "market_value": 100},
    ]
    monkeypatch.chdir(tmp_path)
    mgr = make_manager(monkeypatch, positions)
    targets = mgr.determine_target_weights()
    assert targets == {"AAPL": 0.5, "MSFT": 0.5}
    state = json.loads(Path("portfolio_state.json").read_text())
    assert state == targets


def test_rebalance_portfolio_triggers_orders(monkeypatch):
    positions = [
        {"symbol": "AAPL", "market_value": 600, "current_price": 60},
        {"symbol": "MSFT", "market_value": 400, "current_price": 40},
    ]
    mgr = make_manager(monkeypatch, positions)
    mgr.rebalance_portfolio({"AAPL": 0.5, "MSFT": 0.5}, threshold=0.05)
    assert len(mgr.client.orders) == 2
    sides = {order[0]: order[2] for order in mgr.client.orders}
    assert sides["AAPL"] == "sell"
    assert sides["MSFT"] == "buy"
