import json
from services.trading_daemon import TradingDaemon


class DummyBot:
    async def run(self, symbols=None):
        pass


def test_metrics_reset(tmp_path):
    state_file = tmp_path / "state.json"
    daemon = TradingDaemon(DummyBot(), state_path=state_file)
    daemon.record_trade(5)
    assert json.loads(state_file.read_text())["trade_count"] == 1

    # Force reset by simulating new day
    daemon.state.date = "1900-01-01"
    daemon.save_state()
    daemon.load_state()
    assert daemon.state.trade_count == 0
    assert daemon.state.profit == 0
