import json
from fundrunner.bots.chatgpt_trading_controller import run_chatgpt_controller

class DummyPM:
    def view_account(self):
        return {"cash": 1000}

    def view_positions(self):
        return [{"symbol": "AAPL", "qty": 1, "market_value": 100, "unrealized_pl_percent": 10}]

class DummyTM:
    def __init__(self):
        self.actions = []

    def buy(self, symbol, qty, order_type='market', time_in_force='gtc'):
        self.actions.append(("buy", symbol, qty))

    def sell(self, symbol, qty, order_type='market', time_in_force='gtc'):
        self.actions.append(("sell", symbol, qty))

def test_gpt_response_triggers_trades(monkeypatch):
    response = json.dumps({"actions": [{"action": "buy", "symbol": "MSFT", "quantity": 2}], "request": "done"})
    monkeypatch.setattr('fundrunner.bots.chatgpt_trading_controller.ask_gpt', lambda prompt: response)
    monkeypatch.setattr('fundrunner.bots.chatgpt_trading_controller.PortfolioManager', lambda: DummyPM())
    dummy = DummyTM()
    monkeypatch.setattr('fundrunner.bots.chatgpt_trading_controller.TradeManager', lambda: dummy)
    run_chatgpt_controller(max_cycles=1)
    assert dummy.actions == [("buy", "MSFT", 2)]

