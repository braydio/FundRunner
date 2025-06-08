
# portfolio_manager.py
from alpaca.api_client import AlpacaClient

class PortfolioManager:
    def __init__(self):
        self.client = AlpacaClient()

    def view_account(self):
        return self.client.get_account()

    def view_positions(self):
        return self.client.list_positions()

    def view_position(self, symbol):
        return self.client.get_position(symbol)

