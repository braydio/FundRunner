"""Service for retrieving stock lending rates from Alpaca.

The :class:`LendingRateService` attempts to fetch current lending rates
via the Alpaca API using credentials supplied through environment
variables. If the live request fails for any reason, deterministic stub
rates are returned instead. This allows dependent components to continue
operating in development or offline scenarios.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List

import requests

from fundrunner.utils.error_handling import ErrorType, FundRunnerError

logger = logging.getLogger(__name__)


class LendingRateService:
    """Fetch stock lending rates from Alpaca with graceful fallbacks."""

    def __init__(self) -> None:
        self.api_key = os.getenv("APCA_API_KEY_ID")
        self.api_secret = os.getenv("APCA_API_SECRET_KEY")
        self.base_url = os.getenv(
            "APCA_API_BASE_URL", "https://paper-api.alpaca.markets"
        )

    def fetch_live_rates(self, symbols: List[str]) -> Dict[str, float]:
        """Return live lending rates for each symbol.

        Args:
            symbols: List of ticker symbols.

        Returns:
            Mapping of symbol to lending rate.

        Raises:
            FundRunnerError: If credentials are missing or request fails.
        """

        if not self.api_key or not self.api_secret:
            raise FundRunnerError(
                "Missing Alpaca API credentials",
                error_type=ErrorType.API_AUTHENTICATION,
            )

        if not symbols:
            return {}

        url = f"{self.base_url.rstrip('/')}/v1beta1/stock-lending/rates"
        headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.api_secret,
        }
        params = {"symbols": ",".join(symbols)}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            rates: Dict[str, float] = {}

            # Accept either a list of dicts or symbol: rate mapping
            items = data.get("rates") if isinstance(data, dict) else data
            if isinstance(items, list):
                for item in items:
                    symbol = item.get("symbol")
                    rate = item.get("rate")
                    if symbol and rate is not None:
                        try:
                            rates[symbol] = float(rate)
                        except (TypeError, ValueError):
                            logger.debug("Non-numeric rate for %s: %s", symbol, rate)
            elif isinstance(items, dict):
                for symbol, rate in items.items():
                    try:
                        rates[symbol] = float(rate)
                    except (TypeError, ValueError):
                        logger.debug("Non-numeric rate for %s: %s", symbol, rate)
            else:
                raise FundRunnerError(
                    "Unexpected response format from lending rates API",
                    error_type=ErrorType.API_INVALID_REQUEST,
                    details={"response": data},
                )

            return rates
        except requests.RequestException as exc:
            logger.error("Lending rate API request failed: %s", exc)
            raise FundRunnerError(
                "Failed to fetch lending rates",
                error_type=ErrorType.API_CONNECTION,
                original_exception=exc,
            ) from exc

    def fetch_stub_rates(self, symbols: List[str]) -> Dict[str, float]:
        """Return deterministic stub lending rates for given symbols."""

        rates: Dict[str, float] = {}
        for idx, symbol in enumerate(symbols):
            rates[symbol] = round(0.01 + idx * 0.005, 4)
        return rates

    def get_rates(self, symbols: List[str]) -> Dict[str, float]:
        """Fetch live lending rates, falling back to stub rates on error."""

        try:
            return self.fetch_live_rates(symbols)
        except FundRunnerError as exc:  # pragma: no cover - logging and fallback
            logger.warning("Falling back to stub lending rates: %s", exc)
            return self.fetch_stub_rates(symbols)
