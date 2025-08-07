"""Helpers for managing Alpaca watchlists."""

from fundrunner.alpaca.api_client import AlpacaClient

class WatchlistManager:
    def __init__(self):
        self.client = AlpacaClient()

    def list_watchlists(self):
        return self.client.list_watchlists()

    def create_watchlist(self, watchlist_name, symbols):
        return self.client.create_watchlist(watchlist_name, symbols)

    def add_to_watchlist(self, watchlist_id, symbol):
        return self.client.add_to_watchlist(watchlist_id, symbol)

    def remove_from_watchlist(self, watchlist_id, symbol):
        return self.client.remove_from_watchlist(watchlist_id, symbol)

    def get_watchlist(self, watchlist_id):
        return self.client.get_watchlist(watchlist_id)

    def delete_watchlist(self, watchlist_id):
        return self.client.delete_watchlist(watchlist_id)
