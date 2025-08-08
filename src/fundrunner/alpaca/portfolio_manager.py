"""Alpaca portfolio utilities and allocation helpers."""

from collections import defaultdict
from typing import Dict

from fundrunner.alpaca.api_client import AlpacaClient
from fundrunner.utils import config


class PortfolioManager:
    """Client wrapper and portfolio allocation utilities."""

    def __init__(self) -> None:
        self.client = AlpacaClient()

    def view_account(self):
        """Return the account summary from Alpaca."""
        return self.client.get_account()

    def view_positions(self):
        """Return all current positions from Alpaca."""
        return self.client.list_positions()

    def view_position(self, symbol):
        """Return a single position by ticker symbol."""
        return self.client.get_position(symbol)

    def determine_target_weights(self, sector_map: Dict[str, str]) -> Dict[str, float]:
        """Determine target weights for a set of tickers.

        Parameters
        ----------
        sector_map:
            Mapping of ticker symbols to their sector names. The mapping is
            used when `config.SECTOR_MODE` is enabled.

        Returns
        -------
        dict
            A mapping of ticker symbols to target weights that sum to 1.

        Notes
        -----
        When ``config.SECTOR_MODE`` is ``True`` each sector receives equal
        weight and that weight is split equally among tickers within the
        sector. Otherwise, all tickers are equally weighted regardless of
        sector.
        """

        if not sector_map:
            return {}

        if config.SECTOR_MODE:
            sectors: Dict[str, list[str]] = defaultdict(list)
            for ticker, sector in sector_map.items():
                sectors[sector].append(ticker)
            per_sector = 1 / len(sectors)
            weights: Dict[str, float] = {}
            for tickers in sectors.values():
                per_ticker = per_sector / len(tickers)
                for ticker in tickers:
                    weights[ticker] = per_ticker
            return weights

        # Default: equal weight across tickers
        per_ticker = 1 / len(sector_map)
        return {ticker: per_ticker for ticker in sector_map}

