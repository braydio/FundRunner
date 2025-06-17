import pandas as pd
from alpaca.api_client import AlpacaClient
from alpaca_trade_api.rest import TimeFrame
import alpaca.api_client as api_mod

class DummyREST:
    def __init__(self, *args, **kwargs):
        pass
    def get_bars(self, symbol, timeframe, start, end):
        self.called_with = {
            'symbol': symbol,
            'timeframe': timeframe,
            'start': start,
            'end': end
        }
        return type('Result', (), {'df': pd.DataFrame({'open':[1], 'close':[1]})})()

def test_get_historical_bars_format(monkeypatch):
    dummy = DummyREST()
    monkeypatch.setattr(api_mod.tradeapi, 'REST', lambda *a, **k: dummy)
    client = AlpacaClient()
    df = client.get_historical_bars('AAPL', days=1, timeframe=TimeFrame.Day)
    assert isinstance(df, pd.DataFrame)
    args = dummy.called_with
    assert args['start'].endswith('Z')
    assert args['end'].endswith('Z')
    assert '.' not in args['start'] and '.' not in args['end']

