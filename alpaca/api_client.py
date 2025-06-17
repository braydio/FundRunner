# api_client.py
"""Wrapper around :mod:`alpaca_trade_api` providing convenience helpers."""

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame
from config import API_KEY, API_SECRET, BASE_URL
import logging
import requests

# Configure logging for this module
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create a console handler with a warning log level so debug info is not printed to terminal
ch = logging.StreamHandler()
ch.setLevel(logging.WARNING)

# Create a formatter and attach it to the handler
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)

# Add the handler to the logger if it's not already added
if not logger.hasHandlers():
    logger.addHandler(ch)


class AlpacaClient:
    def __init__(self):
        logger.debug(
            "Initializing AlpacaClient with BASE_URL: %s and API_KEY: %s",
            BASE_URL,
            API_KEY,
        )
        self.api = tradeapi.REST(API_KEY, API_SECRET, BASE_URL, api_version="v2")

    def safe_float(self, val, default=0.0):
        try:
            account = self.api.get_account()
            logger.debug("Account raw: %s", account._raw)
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    def get_account(self):
        logger.debug("Fetching account information via GET /account")
        try:
            account = self.api.get_account()
            logger.debug("Account fetched successfully: %s", account)
            # Sanitize and return only the relevant fields
            sanitized_account = {
                "cash": self.safe_float(account.cash),
                "buying_power": self.safe_float(account.buying_power),
                "equity": self.safe_float(account.equity),
                "portfolio_value": self.safe_float(account.portfolio_value),
            }
            logger.debug("Sanitized account: %s", sanitized_account)
            return sanitized_account
        except Exception as e:
            logger.error("Error fetching account information: %s", e, exc_info=True)
            raise

    def submit_order(self, symbol, qty, side, order_type, time_in_force):
        """Submit an order via the Alpaca REST API.

        Fractional share orders must use ``DAY`` time in force.  This method
        automatically switches the ``time_in_force`` to ``day`` when a
        fractional ``qty`` is detected.
        """

        logger.debug(
            "Submitting order: side=%s, qty=%s, symbol=%s, order_type=%s, time_in_force=%s",
            side,
            qty,
            symbol,
            order_type,
            time_in_force,
        )

        try:
            qty_val = float(qty)
            if qty_val % 1 != 0 and time_in_force.lower() != "day":
                logger.debug(
                    "Overriding time_in_force to 'day' for fractional qty %s", qty
                )
                time_in_force = "day"
        except Exception:
            # If conversion fails, just proceed with provided values
            pass

        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
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
            sanitized_positions = []
            for pos in positions:
                sanitized_positions.append(
                    {
                        "symbol": pos.symbol,
                        "qty": self.safe_float(pos.qty),
                        "market_value": self.safe_float(pos.market_value),
                        "unrealized_pl_percent": self.safe_float(
                            getattr(pos, "unrealized_plpc", 0)
                        )
                        * 100,
                    }
                )
            logger.debug("Sanitized positions: %s", sanitized_positions)
            return sanitized_positions
        except Exception as e:
            logger.error("Error listing positions: %s", e, exc_info=True)
            raise

    def get_position(self, symbol):
        logger.debug("Getting position for symbol: %s", symbol)
        try:
            position = self.api.get_position(symbol)
            sanitized_position = {
                "symbol": position.symbol,
                "qty": self.safe_float(position.qty),
                "market_value": self.safe_float(position.market_value),
                "unrealized_pl_percent": self.safe_float(
                    getattr(position, "unrealized_plpc", 0)
                )
                * 100,
            }
            logger.debug("Sanitized position: %s", sanitized_position)
            return sanitized_position
        except Exception as e:
            logger.error(
                "Error getting position for symbol %s: %s", symbol, e, exc_info=True
            )
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

    def list_orders(self, status="open"):
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
            matching = [
                w for w in watchlists if w.name.lower() == watchlist_identifier.lower()
            ]
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
            logger.debug(
                "Symbol %s removed from watchlist %s: %s", symbol, watchlist_id, result
            )
            return result
        except Exception as e:
            logger.error(
                "Error removing symbol %s from watchlist %s: %s",
                symbol,
                watchlist_id,
                e,
                exc_info=True,
            )
            raise

    def get_watchlist(self, watchlist_id):
        logger.debug("Fetching watchlist with ID: %s", watchlist_id)
        try:
            wl = self.api.get_watchlist(watchlist_id)
            logger.debug("Watchlist retrieved: %s", wl)
            return wl
        except Exception as e:
            logger.error(
                "Error fetching watchlist %s: %s", watchlist_id, e, exc_info=True
            )
            raise

    def delete_watchlist(self, watchlist_id):
        logger.debug("Deleting watchlist with ID: %s", watchlist_id)
        try:
            result = self.api.delete_watchlist(watchlist_id)
            logger.debug("Watchlist deleted: %s", result)
            return result
        except Exception as e:
            logger.error(
                "Error deleting watchlist %s: %s", watchlist_id, e, exc_info=True
            )
            raise

    def get_historical_bars(self, symbol, days=30, timeframe=tradeapi.rest.TimeFrame.Day):
        """Return historical bars for the given symbol.

        Parameters
        ----------
        symbol : str
            The ticker to query.
        days : int, optional
            Number of days of data to retrieve, by default 30.
        timeframe : TimeFrame, optional
            Bar timeframe, by default ``TimeFrame.Day``.

        Returns
        -------
        pandas.DataFrame | None
            DataFrame of bar data indexed by time or ``None`` if retrieval fails.
        """
        from datetime import datetime, timedelta

        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=days)
        start = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            bars = self.api.get_bars(symbol, timeframe, start, end)
            return bars.df if hasattr(bars, "df") else None
        except Exception as e:
            logger.error("Error fetching historical bars for %s: %s", symbol, e, exc_info=True)
            return None

    def get_latest_price(self, symbol):
        """Return the latest trade price for ``symbol`` or ``None`` if unavailable."""
        try:
            bar = self.api.get_latest_bar(symbol)
            return float(getattr(bar, "c", None)) if bar is not None else None
        except Exception as e:
            logger.error("Error fetching latest price for %s: %s", symbol, e, exc_info=True)
            return None

