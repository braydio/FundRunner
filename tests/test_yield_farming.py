import pytest
from datetime import datetime

from alpaca.yield_farming import YieldFarmer


class DummyClient:
    def __init__(self):
        self.account = {"cash": 1000.0}

    def get_account(self):
        return self.account

    def get_latest_price(self, symbol):
        return 100.0


def test_build_lending_portfolio(monkeypatch):
    farmer = YieldFarmer(client=DummyClient())
    monkeypatch.setattr(
        farmer, "fetch_lending_rates", lambda: {"AAA": 0.03, "BBB": 0.02}
    )
    portfolio = farmer.build_lending_portfolio(allocation_percent=0.5, top_n=2)
    assert len(portfolio) == 2
    assert portfolio[0]["qty"] > 0


def test_build_dividend_portfolio_active(monkeypatch):
    farmer = YieldFarmer(client=DummyClient())
    data = {
        "AAA": (0.05, datetime(2025, 7, 1)),
        "BBB": (0.04, datetime(2025, 6, 1)),
    }
    monkeypatch.setattr(
        farmer,
        "fetch_dividend_info",
        lambda sym: data[sym],
    )
    portfolio = farmer.build_dividend_portfolio(
        ["AAA", "BBB"], allocation_percent=0.5, active=True
    )
    assert portfolio[0]["symbol"] == "BBB"
