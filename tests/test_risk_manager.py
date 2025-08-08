import pandas as pd
import pytest

from fundrunner.alpaca.risk_manager import RiskManager


class DummyClient:
    def get_bars(self, symbol, start, end):
        return pd.DataFrame(
            {
                "close": [100, 104, 112.32, 110.0736],
                "volume": [500_000, 500_000, 500_000, 500_000],
            }
        )


def test_allocation_limit_adjusts_for_vol_and_volume():
    client = DummyClient()
    manager = RiskManager(client=client)
    limit = manager.allocation_limit("AAPL")

    data = client.get_bars("AAPL", None, None)
    data["Return"] = data["close"].pct_change()
    vol = data["Return"].std()
    expected = manager.base_allocation_limit
    if vol > 0:
        expected *= min(0.02 / vol, 1)
    expected = max(expected, manager.minimum_allocation)
    if data["volume"].mean() < 1e6:
        expected *= 0.8

    assert limit == pytest.approx(expected)
