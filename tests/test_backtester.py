import fundrunner.backtester as backtester


class DummyClient:
    def __init__(self):
        self.data = {
            "AAPL": [
                {"t": "2023-01-01", "o": 100.0, "c": 102.0},
                {"t": "2023-01-02", "o": 102.0, "c": 104.0},
            ],
            "MSFT": [
                {"t": "2023-01-01", "o": 200.0, "c": 198.0},
                {"t": "2023-01-02", "o": 198.0, "c": 202.0},
            ],
        }

    def get_bars(self, symbol, start_date, end_date):
        return self.data.get(symbol, [])


def test_run_backtest(monkeypatch=None):
    backtester.AlpacaClient = lambda: DummyClient()
    result = backtester.run_backtest(
        "AAPL", "2023-01-01", "2023-01-03", initial_capital=1000, allocation_limit=0.1
    )
    assert result["num_trades"] == 2
    assert result["final_capital"] > 1000
    assert "cagr" in result and "max_drawdown" in result


def test_backtest_portfolio(monkeypatch=None):
    backtester.AlpacaClient = lambda: DummyClient()
    result = backtester.backtest_portfolio(
        ["AAPL", "MSFT"],
        {"AAPL": 0.5, "MSFT": 0.5},
        "2023-01-01",
        "2023-01-03",
        initial_capital=1000,
        rebalance_frequency=1,
        rebalance_threshold=0.05,
    )
    assert result["final_value"] > 0
    assert result["cagr"] >= 0
    assert result["max_drawdown"] >= 0


if __name__ == "__main__":
    test_run_backtest()
    test_backtest_portfolio()
    print("All tests passed.")
