"""Utilities for fetching stock lending rates from Alpaca with fallbacks."""

from __future__ import annotations

import logging
from typing import Dict, Any

import requests

from fundrunner.utils.config import API_KEY, API_SECRET, BASE_URL

logger = logging.getLogger(__name__)


def fetch_lending_rates() -> Dict[str, float]:
    """Return stock lending rates keyed by symbol.

    Attempts to query Alpaca's ``/v2/portfolio/stock_lending`` endpoint and
    validates the expected response schema.  If the request fails or the schema
    is malformed, realistic stub data is returned instead.
    """

    endpoint = f"{BASE_URL}/v2/portfolio/stock_lending"
    headers = {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": API_SECRET,
    }
    try:
        resp = requests.get(endpoint, headers=headers, timeout=10)
        resp.raise_for_status()
        data: Any = resp.json()
        if isinstance(data, dict):
            rates = data.get("rates")
            if isinstance(rates, list):
                parsed: Dict[str, float] = {}
                for item in rates:
                    sym = item.get("symbol")
                    rate = item.get("rate")
                    if isinstance(sym, str) and isinstance(rate, (int, float)):
                        parsed[sym] = float(rate)
                if parsed:
                    return parsed
            logger.warning("Unexpected schema in lending rates response: %s", data)
    except requests.RequestException as exc:  # pragma: no cover - network failure
        logger.warning("Failed to fetch lending rates: %s", exc)
    except ValueError as exc:  # pragma: no cover - JSON decode
        logger.warning("Failed to parse lending rates: %s", exc)

    # Fallback stub data with realistic spreads
    return {
        "AAPL": 0.027,
        "MSFT": 0.022,
        "GOOGL": 0.019,
        "TSLA": 0.031,
        "AMZN": 0.017,
    }
