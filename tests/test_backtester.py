import fundrunner.backtester as backtester

class DummyClient:
    def get_bars(self, symbol, start_date, end_date):
        return [
            {"t": "2023-01-01", "o": 100.0, "c": 102.0},
            {"t": "2023-01-02", "o": 102.0, "c": 104.0},
        ]


def test_run_backtest(monkeypatch=None):
    backtester.AlpacaClient = lambda: DummyClient()
    result = backtester.run_backtest("AAPL", "2023-01-01", "2023-01-03", initial_capital=1000, allocation_limit=0.1)
    assert result["num_trades"] == 2
    assert result["final_capital"] > 1000

if __name__ == "__main__":
    test_run_backtest()
    print("All tests passed.")
