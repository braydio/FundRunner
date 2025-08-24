import fundrunner.alpaca.api_client as api_mod


class DummyREST:
    def __init__(self, *args, **kwargs):
        pass

    def list_positions(self):
        class Pos:
            symbol = "AAPL"
            qty = 1
            market_value = 100
            unrealized_plpc = 0.1
            avg_entry_price = 90
            current_price = 100

        return [Pos()]

    def get_position(self, symbol):
        return type(
            "Pos",
            (),
            {
                "symbol": symbol,
                "qty": 2,
                "market_value": 200,
                "unrealized_plpc": 0.2,
                "avg_entry_price": 95,
                "current_price": 100,
            },
        )()


def test_position_fields(monkeypatch):
    monkeypatch.setattr(api_mod.tradeapi, "REST", lambda *a, **k: DummyREST())
    client = api_mod.AlpacaClient()
    positions = client.list_positions()
    assert positions[0]["avg_entry_price"] == 90
    assert positions[0]["current_price"] == 100

    pos = client.get_position("AAPL")
    assert pos["avg_entry_price"] == 95
    assert pos["current_price"] == 100
