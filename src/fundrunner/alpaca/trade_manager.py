"""Convenience wrapper for submitting Alpaca trade orders."""

from fundrunner.alpaca.api_client import AlpacaClient

class TradeManager:
    def __init__(self):
        self.client = AlpacaClient()

    def buy(self, symbol, qty, order_type='market', time_in_force='gtc'):
        return self.client.submit_order(symbol, qty, 'buy', order_type, time_in_force)

    def sell(self, symbol, qty, order_type='market', time_in_force='gtc'):
        return self.client.submit_order(symbol, qty, 'sell', order_type, time_in_force)

    def cancel_order(self, order_id):
        return self.client.cancel_order(order_id)

    def list_open_orders(self):
        return self.client.list_orders(status='open')

