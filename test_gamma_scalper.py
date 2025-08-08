import pytest

from alpaca.gamma_scalper import GammaScalper


class DummyPortfolio:
    def view_positions(self):
        return [
            {"symbol": "AAPL", "delta": 0.6, "qty": 1},
            {"symbol": "AAPL", "delta": 0.2, "qty": 1},
        ]


class DummyTrader:
    def __init__(self):
        self.orders = []

    def buy(self, symbol, qty):
        self.orders.append(("buy", symbol, qty))

    def sell(self, symbol, qty):
        self.orders.append(("sell", symbol, qty))


def test_gamma_scalper_places_hedge_order():
    trader = DummyTrader()
    scalper = GammaScalper(DummyPortfolio(), trader)
    orders = scalper.run("AAPL", target_delta=0.0, threshold=0.1)
    assert orders
    assert trader.orders  # ensure an order was executed
