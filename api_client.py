# api_client.py
import alpaca_trade_api as tradeapi
from config import API_KEY, API_SECRET, BASE_URL
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a console handler with a debug log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create a formatter and attach it to the handler
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handler to the logger if it's not already added
if not logger.hasHandlers():
    logger.addHandler(ch)

class AlpacaClient:
    def __init__(self):
        logger.debug("Initializing AlpacaClient with BASE_URL: %s and API_KEY: %s", BASE_URL, API_KEY)
        self.api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version='v2')

    def get_account(self):
        logger.debug("Fetching account information via GET /account")
        try:
            account = self.api.get_account()
            logger.debug("Account fetched successfully: %s", account)
            return account
        except Exception as e:
            logger.error("Error fetching account information: %s", e, exc_info=True)
            raise

    def submit_order(self, symbol, qty, side, order_type, time_in_force):
        logger.debug("Submitting order: side=%s, qty=%s, symbol=%s, order_type=%s, time_in_force=%s",
                     side, qty, symbol, order_type, time_in_force)
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force
            )
            logger.debug("Order submitted successfully: %s", order)
            return order
        except Exception as e:
            logger.error("Error submitting order: %s", e, exc_info=True)
            raise

    def list_positions(self):
        logger.debug("Listing all positions via GET /positions")
        try:
            positions = self.api.list_positions()
            logger.debug("Positions retrieved: %s", positions)
            return positions
        except Exception as e:
            logger.error("Error listing positions: %s", e, exc_info=True)
            raise

    def get_position(self, symbol):
        logger.debug("Getting position for symbol: %s", symbol)
        try:
            position = self.api.get_position(symbol)
            logger.debug("Position for %s: %s", symbol, position)
            return position
        except Exception as e:
            logger.error("Error getting position for symbol %s: %s", symbol, e, exc_info=True)
            return None

    def cancel_order(self, order_id):
        logger.debug("Canceling order with ID: %s", order_id)
        try:
            result = self.api.cancel_order(order_id)
            logger.debug("Order canceled: %s", result)
            return result
        except Exception as e:
            logger.error("Error canceling order %s: %s", order_id, e, exc_info=True)
            raise

    def list_orders(self, status='open'):
        logger.debug("Listing orders with status: %s", status)
        try:
            orders = self.api.list_orders(status=status)
            logger.debug("Orders retrieved: %s", orders)
            return orders
        except Exception as e:
            logger.error("Error listing orders: %s", e, exc_info=True)
            raise

    def list_watchlists(self):
        logger.debug("Listing all watchlists")
        try:
            watchlists = self.api.list_watchlists()
            logger.debug("Watchlists retrieved: %s", watchlists)
            return watchlists
        except Exception as e:
            logger.error("Error listing watchlists: %s", e, exc_info=True)
            raise

    def create_watchlist(self, name, symbols):
        logger.debug("Creating watchlist with name: %s and symbols: %s", name, symbols)
        try:
            wl = self.api.create_watchlist(name=name, symbols=symbols)
            logger.debug("Watchlist created successfully: %s", wl)
            return wl
        except Exception as e:
            logger.error("Error creating watchlist: %s", e, exc_info=True)
            raise

    def add_to_watchlist(self, watchlist_identifier, symbol):
        if not str(watchlist_identifier).isdigit():
            watchlists = self.api.list_watchlists()
            matching = [w for w in watchlists if w.name.lower() == watchlist_identifier.lower()]
            if matching:
                watchlist_id = matching[0].id
            else:
                raise ValueError(f"No watchlist found with name {watchlist_identifier}")
        else:
            watchlist_id = watchlist_identifier

        result = self.api.add_to_watchlist(watchlist_id, symbol)
        return result

    def remove_from_watchlist(self, watchlist_id, symbol):
        logger.debug("Removing symbol %s from watchlist %s", symbol, watchlist_id)
        try:
            result = self.api.remove_from_watchlist(watchlist_id, symbol)
            logger.debug("Symbol %s removed from watchlist %s: %s", symbol, watchlist_id, result)
            return result
        except Exception as e:
            logger.error("Error removing symbol %s from watchlist %s: %s", symbol, watchlist_id, e, exc_info=True)
            raise

    def get_watchlist(self, watchlist_id):
        logger.debug("Fetching watchlist with ID: %s", watchlist_id)
        try:
            wl = self.api.get_watchlist(watchlist_id)
            logger.debug("Watchlist retrieved: %s", wl)
            return wl
        except Exception as e:
            logger.error("Error fetching watchlist %s: %s", watchlist_id, e, exc_info=True)
            raise

    def delete_watchlist(self, watchlist_id):
        logger.debug("Deleting watchlist with ID: %s", watchlist_id)
        try:
            result = self.api.delete_watchlist(watchlist_id)
            logger.debug("Watchlist deleted: %s", result)
            return result
        except Exception as e:
            logger.error("Error deleting watchlist %s: %s", watchlist_id, e, exc_info=True)
            raise
